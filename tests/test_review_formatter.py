import pytest

from src.ai_reviewer import ReviewComment, ReviewResult
from src.review_formatter import (
    build_review_event,
    format_inline_comment,
    format_review_summary,
    format_github_review_comments,
)


def make_comment(severity="warning", category="bug"):
    return ReviewComment(
        file="src/main.py",
        line=10,
        severity=severity,
        category=category,
        body="Test comment body",
    )


def make_result(risk_level="medium", approval=False, comments=None):
    return ReviewResult(
        summary="Overall the code looks good.",
        risk_level=risk_level,
        comments=comments or [],
        approval=approval,
    )


class TestFormatInlineComment:
    def test_error_comment(self):
        c = make_comment(severity="error", category="bug")
        result = format_inline_comment(c)
        assert "🐛" in result
        assert "Error" in result
        assert "Test comment body" in result

    def test_warning_comment(self):
        c = make_comment(severity="warning", category="security")
        result = format_inline_comment(c)
        assert "⚠️" in result
        assert "Warning" in result

    def test_suggestion_comment(self):
        c = make_comment(severity="suggestion", category="performance")
        result = format_inline_comment(c)
        assert "💡" in result
        assert "Suggestion" in result

    def test_praise_comment(self):
        c = make_comment(severity="praise", category="best_practice")
        result = format_inline_comment(c)
        assert "👍" in result
        assert "Praise" in result


class TestFormatReviewSummary:
    def test_basic_summary(self):
        result = make_result(comments=[make_comment()])
        summary = format_review_summary(result, model_name="gpt-4o", files_reviewed=5)
        assert "AI Code Review" in summary
        assert "gpt-4o" in summary
        assert "5" in summary

    def test_risk_level_display(self):
        result = make_result(risk_level="high")
        summary = format_review_summary(result)
        assert "🔴" in summary

    def test_low_risk(self):
        result = make_result(risk_level="low")
        summary = format_review_summary(result)
        assert "🟢" in summary

    def test_stats_included(self):
        comments = [
            make_comment(severity="error", category="bug"),
            make_comment(severity="warning", category="security"),
            make_comment(severity="suggestion", category="performance"),
        ]
        result = make_result(comments=comments)
        summary = format_review_summary(result, files_reviewed=3)
        assert "审查文件数" in summary
        assert "发现问题数" in summary

    def test_no_comments(self):
        result = make_result(comments=[])
        summary = format_review_summary(result)
        assert "No issues found" in summary


class TestBuildReviewEvent:
    def test_approve(self):
        result = make_result(risk_level="low", approval=True)
        assert build_review_event(result) == "APPROVE"

    def test_request_changes_high(self):
        result = make_result(risk_level="high")
        assert build_review_event(result) == "REQUEST_CHANGES"

    def test_request_changes_critical(self):
        result = make_result(risk_level="critical")
        assert build_review_event(result) == "REQUEST_CHANGES"

    def test_comment_medium(self):
        result = make_result(risk_level="medium")
        assert build_review_event(result) == "COMMENT"

    def test_comment_low_not_approved(self):
        result = make_result(risk_level="low", approval=False)
        assert build_review_event(result) == "COMMENT"


class TestFormatGithubReviewComments:
    def test_converts_comments(self):
        comments = [make_comment(), make_comment(severity="error")]
        result = make_result(comments=comments)
        gh_comments = format_github_review_comments(result)
        assert len(gh_comments) == 2
        assert gh_comments[0]["path"] == "src/main.py"
        assert gh_comments[0]["line"] == 10

    def test_excludes_praise(self):
        comments = [
            make_comment(severity="praise"),
            make_comment(severity="error"),
        ]
        result = make_result(comments=comments)
        gh_comments = format_github_review_comments(result)
        assert len(gh_comments) == 1

    def test_empty_comments(self):
        result = make_result(comments=[])
        gh_comments = format_github_review_comments(result)
        assert gh_comments == []
