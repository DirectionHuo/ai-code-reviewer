import fnmatch
import logging
import re
from dataclasses import dataclass, field

from .config import DEFAULT_IGNORE_PATTERNS

logger = logging.getLogger(__name__)


@dataclass
class DiffHunk:
    start_line: int
    end_line: int
    content: str


@dataclass
class FileDiff:
    filename: str
    status: str  # added, modified, deleted, renamed
    patch: str
    additions: int
    deletions: int
    hunks: list[DiffHunk] = field(default_factory=list)


def parse_patch(patch: str) -> list[DiffHunk]:
    if not patch:
        return []

    hunks: list[DiffHunk] = []
    hunk_header_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    current_lines: list[str] = []
    current_start = 0
    current_line = 0

    for line in patch.split("\n"):
        match = hunk_header_re.match(line)
        if match:
            if current_lines:
                hunks.append(DiffHunk(
                    start_line=current_start,
                    end_line=current_line,
                    content="\n".join(current_lines),
                ))
            current_start = int(match.group(1))
            current_line = current_start - 1
            current_lines = [line]
        else:
            current_lines.append(line)
            if not line.startswith("-"):
                current_line += 1

    if current_lines:
        hunks.append(DiffHunk(
            start_line=current_start,
            end_line=current_line,
            content="\n".join(current_lines),
        ))

    return hunks


def count_changes(patch: str) -> tuple[int, int]:
    additions = 0
    deletions = 0
    for line in patch.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            additions += 1
        elif line.startswith("-") and not line.startswith("---"):
            deletions += 1
    return additions, deletions


def should_ignore_file(
    filename: str, custom_patterns: list[str] | None = None
) -> bool:
    patterns = DEFAULT_IGNORE_PATTERNS + (custom_patterns or [])
    basename = filename.split("/")[-1]

    for pattern in patterns:
        if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(filename, pattern):
            return True

    return False


def parse_pr_files(
    pr_files: list[dict],
    custom_ignore_patterns: list[str] | None = None,
    max_files: int = 20,
    max_diff_size: int = 500,
) -> list[FileDiff]:
    parsed: list[FileDiff] = []

    for file_info in pr_files[:max_files]:
        filename = file_info.get("filename", "")
        status = file_info.get("status", "modified")
        patch = file_info.get("patch", "")

        if not patch:
            logger.info("Skipping %s: no patch content (binary or empty)", filename)
            continue

        if should_ignore_file(filename, custom_ignore_patterns):
            logger.info("Skipping %s: matched ignore pattern", filename)
            continue

        additions, deletions = count_changes(patch)
        total_changes = additions + deletions

        if total_changes > max_diff_size:
            logger.warning(
                "File %s has %d changed lines (limit: %d), will be summarized",
                filename,
                total_changes,
                max_diff_size,
            )

        hunks = parse_patch(patch)

        parsed.append(FileDiff(
            filename=filename,
            status=status,
            patch=patch,
            additions=additions,
            deletions=deletions,
            hunks=hunks,
        ))

    if len(pr_files) > max_files:
        logger.warning(
            "PR has %d files, only reviewing first %d", len(pr_files), max_files
        )

    return parsed
