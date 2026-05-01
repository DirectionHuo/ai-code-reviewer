import json
import logging
import os
import sys

from .config import Config
from .diff_parser import parse_pr_files
from .github_client import GitHubClient
from .ai_reviewer import review_pr
from .review_formatter import (
    build_review_event,
    format_github_review_comments,
    format_review_summary,
)

logger = logging.getLogger(__name__)


def get_pr_context() -> tuple[str, int]:
    event_path = os.getenv("GITHUB_EVENT_PATH", "")
    if event_path and os.path.exists(event_path):
        with open(event_path, encoding="utf-8") as f:
            event = json.load(f)
        pr_number = event.get("pull_request", {}).get("number")
        repo = event.get("repository", {}).get("full_name")
        if pr_number and repo:
            return repo, int(pr_number)

    repo = os.getenv("GITHUB_REPOSITORY", "")
    pr_number = os.getenv("PR_NUMBER", "")
    if repo and pr_number:
        return repo, int(pr_number)

    return "", 0


def main() -> int:
    config = Config.from_env()
    config.setup_logging()

    logger.info("=== AI Code Reviewer Started ===")

    errors = config.validate()
    if errors:
        for err in errors:
            logger.error("Config error: %s", err)
        return 1

    repo, pr_number = get_pr_context()
    if not repo or not pr_number:
        logger.error(
            "Cannot determine PR context. Set GITHUB_EVENT_PATH or "
            "GITHUB_REPOSITORY + PR_NUMBER environment variables."
        )
        return 1

    logger.info("Reviewing PR #%d in %s", pr_number, repo)

    github = GitHubClient(config.github_token)

    try:
        pr_info = github.get_pr_info(repo, pr_number)
        logger.info("PR: %s by %s", pr_info["title"], pr_info["author"])
    except Exception as e:
        logger.error("Failed to get PR info: %s", e)
        return 1

    try:
        raw_files = github.get_pr_files(repo, pr_number)
        logger.info("Found %d changed files", len(raw_files))
    except Exception as e:
        logger.error("Failed to get PR files: %s", e)
        return 1

    file_diffs = parse_pr_files(
        raw_files,
        custom_ignore_patterns=config.ignore_patterns,
        max_files=config.max_files,
        max_diff_size=config.max_diff_size,
    )

    if not file_diffs:
        logger.info("No reviewable files found, skipping review")
        return 0

    logger.info("Reviewing %d files", len(file_diffs))

    try:
        review_result = review_pr(config, file_diffs, pr_info)
    except Exception as e:
        logger.error("AI review failed: %s", e)
        return 1

    summary = format_review_summary(
        review_result,
        model_name=config.ai_model,
        files_reviewed=len(file_diffs),
    )
    comments = format_github_review_comments(review_result)
    event = build_review_event(review_result)

    logger.info(
        "Review complete: %s, %d comments, event=%s",
        review_result.risk_level,
        len(comments),
        event,
    )

    try:
        github.submit_review(
            repo=repo,
            pr_number=pr_number,
            comments=comments,
            summary=summary,
            event=event,
            commit_sha=pr_info.get("head_sha", ""),
        )
        logger.info("Review submitted successfully")
    except Exception as e:
        logger.error("Failed to submit review: %s", e)
        return 1

    logger.info("=== AI Code Reviewer Finished ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
