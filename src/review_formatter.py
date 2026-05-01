import logging
from collections import Counter

from .ai_reviewer import ReviewComment, ReviewResult

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "error": "🐛",
    "warning": "⚠️",
    "suggestion": "💡",
    "praise": "👍",
}

CATEGORY_EMOJI = {
    "bug": "🐛",
    "security": "🔒",
    "performance": "⚡",
    "style": "💅",
    "best_practice": "💡",
}

RISK_EMOJI = {
    "low": "🟢 Low",
    "medium": "🟡 Medium",
    "high": "🔴 High",
    "critical": "🔴 Critical",
}


def format_inline_comment(comment: ReviewComment) -> str:
    emoji = SEVERITY_EMOJI.get(comment.severity, "💬")
    cat_emoji = CATEGORY_EMOJI.get(comment.category, "📌")
    severity_label = comment.severity.capitalize()
    category_label = comment.category.replace("_", " ").title()

    return (
        f"{emoji} **[{severity_label}]** {cat_emoji} _{category_label}_\n\n"
        f"{comment.body}"
    )


def format_review_summary(
    result: ReviewResult,
    model_name: str = "",
    files_reviewed: int = 0,
) -> str:
    risk_display = RISK_EMOJI.get(result.risk_level, result.risk_level)

    category_counts = Counter(c.category for c in result.comments)
    severity_counts = Counter(c.severity for c in result.comments)
    issue_count = severity_counts.get("error", 0) + severity_counts.get("warning", 0)
    suggestion_count = severity_counts.get("suggestion", 0)
    praise_count = severity_counts.get("praise", 0)

    stats_parts = []
    for cat, emoji in CATEGORY_EMOJI.items():
        count = category_counts.get(cat, 0)
        if count > 0:
            label = cat.replace("_", " ").title()
            stats_parts.append(f"{emoji} {label}: {count}")

    stats_line = " | ".join(stats_parts) if stats_parts else "No issues found"

    lines = [
        "## 🤖 AI Code Review",
        "",
        f"**风险等级：** {risk_display}",
        "",
        "### 📊 审查统计",
        f"- 审查文件数：{files_reviewed}",
        f"- 发现问题数：{issue_count}",
        f"- 建议数：{suggestion_count}",
        f"- 优秀实践：{praise_count}",
        f"- {stats_line}",
        "",
        "### 📝 总体评价",
        result.summary,
        "",
        "---",
        f"> 🤖 此审查由 AI Code Reviewer 自动生成 | Model: {model_name}",
    ]

    return "\n".join(lines)


def build_review_event(result: ReviewResult) -> str:
    if result.approval and result.risk_level == "low":
        return "APPROVE"
    elif result.risk_level in ("high", "critical"):
        return "REQUEST_CHANGES"
    else:
        return "COMMENT"


def format_github_review_comments(
    result: ReviewResult,
) -> list[dict]:
    comments = []
    for c in result.comments:
        if c.severity == "praise":
            continue
        comments.append({
            "path": c.file,
            "line": c.line,
            "body": format_inline_comment(c),
        })
    return comments
