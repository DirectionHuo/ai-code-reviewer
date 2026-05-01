import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from .config import Config, get_prompt_path
from .diff_parser import FileDiff

logger = logging.getLogger(__name__)


@dataclass
class ReviewComment:
    file: str
    line: int
    severity: str
    category: str
    body: str


@dataclass
class ReviewResult:
    summary: str
    risk_level: str
    comments: list[ReviewComment] = field(default_factory=list)
    approval: bool = True


def load_system_prompt(language: str = "zh-CN") -> str:
    prompt_path = get_prompt_path()
    template = prompt_path.read_text(encoding="utf-8")

    if language.startswith("zh"):
        instruction = "Please write all review comments in Chinese (中文). Use Chinese for the summary, comment bodies, and all descriptive text."
    else:
        instruction = "Please write all review comments in English."

    return template.replace("{review_language_instruction}", instruction)


def build_review_prompt(
    file_diffs: list[FileDiff],
    pr_info: dict,
    max_diff_size: int = 500,
) -> str:
    parts = []
    parts.append(f"## Pull Request Information")
    parts.append(f"- **Title**: {pr_info.get('title', 'N/A')}")
    parts.append(f"- **Author**: {pr_info.get('author', 'N/A')}")
    parts.append(f"- **Branch**: {pr_info.get('head_branch', 'N/A')} → {pr_info.get('base_branch', 'N/A')}")

    description = pr_info.get("body", "")
    if description:
        parts.append(f"- **Description**: {description[:500]}")

    parts.append("")
    parts.append("## Code Changes")
    parts.append("")

    for fd in file_diffs:
        total_changes = fd.additions + fd.deletions
        parts.append(f"### File: `{fd.filename}` ({fd.status})")
        parts.append(f"Changes: +{fd.additions} -{fd.deletions}")
        parts.append("")

        if total_changes > max_diff_size:
            parts.append(f"⚠️ Large diff ({total_changes} lines changed). Showing first {max_diff_size} lines:")
            lines = fd.patch.split("\n")[:max_diff_size]
            parts.append("```diff")
            parts.append("\n".join(lines))
            parts.append("```")
        else:
            parts.append("```diff")
            parts.append(fd.patch)
            parts.append("```")

        parts.append("")

    return "\n".join(parts)


def chunk_file_diffs(
    file_diffs: list[FileDiff], max_chunk_lines: int = 2000
) -> list[list[FileDiff]]:
    chunks: list[list[FileDiff]] = []
    current_chunk: list[FileDiff] = []
    current_lines = 0

    for fd in file_diffs:
        file_lines = fd.additions + fd.deletions
        if current_lines + file_lines > max_chunk_lines and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_lines = 0
        current_chunk.append(fd)
        current_lines += file_lines

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def call_ai_api(
    config: Config,
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3,
) -> dict:
    url = f"{config.ai_api_base.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.ai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": config.ai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(max_retries):
        try:
            resp = requests.post(
                url, headers=headers, json=payload, timeout=120
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = parse_ai_response(content)
            return result
        except (requests.RequestException, KeyError) as e:
            wait = 2 ** attempt
            logger.warning(
                "AI API call failed (attempt %d/%d): %s, retrying in %ds",
                attempt + 1, max_retries, e, wait,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                logger.error("AI API call failed after %d attempts", max_retries)
                raise
        except json.JSONDecodeError as e:
            wait = 2 ** attempt
            logger.warning(
                "AI response JSON parse failed (attempt %d/%d): %s",
                attempt + 1, max_retries, e,
            )
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                logger.error("Failed to parse AI response after %d attempts", max_retries)
                raise

    return {}


def parse_ai_response(content: str) -> dict:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = lines[1:]  # remove opening ```json
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines)

    result = json.loads(content)

    if "summary" not in result:
        result["summary"] = "No summary provided."
    if "risk_level" not in result:
        result["risk_level"] = "medium"
    if "comments" not in result:
        result["comments"] = []
    if "approval" not in result:
        result["approval"] = result.get("risk_level", "medium") == "low"

    valid_comments = []
    for c in result["comments"]:
        if all(k in c for k in ("file", "line", "severity", "category", "body")):
            valid_comments.append(c)
        else:
            logger.warning("Skipping malformed comment: %s", c)
    result["comments"] = valid_comments

    return result


def review_pr(
    config: Config,
    file_diffs: list[FileDiff],
    pr_info: dict,
) -> ReviewResult:
    system_prompt = load_system_prompt(config.review_language)
    chunks = chunk_file_diffs(file_diffs)
    all_comments: list[ReviewComment] = []
    summaries: list[str] = []
    risk_levels: list[str] = []
    approval = True

    logger.info("Reviewing %d files in %d chunk(s)", len(file_diffs), len(chunks))

    for i, chunk in enumerate(chunks):
        logger.info("Processing chunk %d/%d (%d files)", i + 1, len(chunks), len(chunk))
        user_prompt = build_review_prompt(chunk, pr_info, config.max_diff_size)

        try:
            result = call_ai_api(config, system_prompt, user_prompt)
        except Exception as e:
            logger.error("Failed to review chunk %d: %s", i + 1, e)
            filenames = [f.filename for f in chunk]
            summaries.append(f"⚠️ Review failed for files: {', '.join(filenames)}")
            continue

        summaries.append(result.get("summary", ""))
        risk_levels.append(result.get("risk_level", "medium"))
        if not result.get("approval", True):
            approval = False

        for c in result.get("comments", []):
            all_comments.append(ReviewComment(
                file=c["file"],
                line=c["line"],
                severity=c["severity"],
                category=c["category"],
                body=c["body"],
            ))

    overall_risk = _aggregate_risk(risk_levels)
    overall_summary = " ".join(s for s in summaries if s)

    return ReviewResult(
        summary=overall_summary,
        risk_level=overall_risk,
        comments=all_comments,
        approval=approval,
    )


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def _aggregate_risk(levels: list[str]) -> str:
    if not levels:
        return "medium"
    return max(levels, key=lambda x: RISK_ORDER.get(x, 1))
