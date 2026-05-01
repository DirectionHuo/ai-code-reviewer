import json
from unittest.mock import patch, MagicMock

import pytest

from src.ai_reviewer import (
    ReviewComment,
    ReviewResult,
    build_review_prompt,
    chunk_file_diffs,
    load_system_prompt,
    parse_ai_response,
    review_pr,
    _aggregate_risk,
)
from src.diff_parser import FileDiff, DiffHunk
from src.config import Config


VALID_AI_RESPONSE = json.dumps({
    "summary": "Code looks good overall with minor issues.",
    "risk_level": "medium",
    "comments": [
        {
            "file": "src/main.py",
            "line": 10,
            "severity": "warning",
            "category": "bug",
            "body": "Potential null reference here.",
        },
        {
            "file": "src/main.py",
            "line": 25,
            "severity": "suggestion",
            "category": "style",
            "body": "Consider using a more descriptive variable name.",
        },
    ],
    "approval": False,
})


def make_file_diff(filename="test.py", additions=10, deletions=5):
    return FileDiff(
        filename=filename,
        status="modified",
        patch="+new line\n-old line\n context",
        additions=additions,
        deletions=deletions,
        hunks=[DiffHunk(start_line=1, end_line=15, content="+new\n-old")],
    )


class TestLoadSystemPrompt:
    def test_chinese_prompt(self):
        prompt = load_system_prompt("zh-CN")
        assert "Chinese" in prompt or "中文" in prompt

    def test_english_prompt(self):
        prompt = load_system_prompt("en")
        assert "English" in prompt

    def test_prompt_contains_format_spec(self):
        prompt = load_system_prompt("en")
        assert "json" in prompt.lower()


class TestBuildReviewPrompt:
    def test_includes_pr_info(self):
        pr_info = {
            "title": "Add feature X",
            "author": "dev",
            "head_branch": "feature-x",
            "base_branch": "main",
            "body": "This PR adds feature X",
        }
        diffs = [make_file_diff()]
        prompt = build_review_prompt(diffs, pr_info)
        assert "Add feature X" in prompt
        assert "dev" in prompt
        assert "feature-x" in prompt

    def test_includes_diff_content(self):
        diffs = [make_file_diff("src/app.py")]
        prompt = build_review_prompt(diffs, {"title": "test"})
        assert "src/app.py" in prompt
        assert "```diff" in prompt

    def test_large_diff_truncation(self):
        large_diff = make_file_diff(additions=600, deletions=100)
        prompt = build_review_prompt([large_diff], {"title": "test"}, max_diff_size=500)
        assert "Large diff" in prompt


class TestParseAiResponse:
    def test_valid_json(self):
        result = parse_ai_response(VALID_AI_RESPONSE)
        assert result["summary"] == "Code looks good overall with minor issues."
        assert result["risk_level"] == "medium"
        assert len(result["comments"]) == 2
        assert result["approval"] is False

    def test_json_with_markdown_wrapper(self):
        wrapped = f"```json\n{VALID_AI_RESPONSE}\n```"
        result = parse_ai_response(wrapped)
        assert result["summary"] == "Code looks good overall with minor issues."

    def test_missing_fields_filled(self):
        minimal = json.dumps({"comments": []})
        result = parse_ai_response(minimal)
        assert "summary" in result
        assert "risk_level" in result
        assert "approval" in result

    def test_malformed_comments_filtered(self):
        response = json.dumps({
            "summary": "test",
            "risk_level": "low",
            "comments": [
                {"file": "a.py", "line": 1, "severity": "error", "category": "bug", "body": "ok"},
                {"file": "b.py"},  # missing fields
            ],
            "approval": True,
        })
        result = parse_ai_response(response)
        assert len(result["comments"]) == 1

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            parse_ai_response("not json at all")


class TestChunkFileDiffs:
    def test_single_chunk(self):
        diffs = [make_file_diff(additions=100, deletions=50)]
        chunks = chunk_file_diffs(diffs, max_chunk_lines=2000)
        assert len(chunks) == 1

    def test_multiple_chunks(self):
        diffs = [make_file_diff(f"file{i}.py", additions=500, deletions=500) for i in range(5)]
        chunks = chunk_file_diffs(diffs, max_chunk_lines=2000)
        assert len(chunks) >= 2

    def test_empty_input(self):
        chunks = chunk_file_diffs([], max_chunk_lines=2000)
        assert chunks == []


class TestAggregateRisk:
    def test_returns_highest(self):
        assert _aggregate_risk(["low", "medium", "high"]) == "high"
        assert _aggregate_risk(["low", "critical"]) == "critical"

    def test_single_level(self):
        assert _aggregate_risk(["low"]) == "low"

    def test_empty_levels(self):
        assert _aggregate_risk([]) == "medium"


class TestReviewPr:
    @patch("src.ai_reviewer.call_ai_api")
    def test_successful_review(self, mock_api):
        mock_api.return_value = json.loads(VALID_AI_RESPONSE)
        config = Config(ai_api_key="test", github_token="test")
        diffs = [make_file_diff()]
        pr_info = {"title": "Test PR", "author": "dev"}

        result = review_pr(config, diffs, pr_info)
        assert isinstance(result, ReviewResult)
        assert len(result.comments) == 2
        assert result.risk_level == "medium"

    @patch("src.ai_reviewer.call_ai_api")
    def test_api_failure_continues(self, mock_api):
        mock_api.side_effect = Exception("API Error")
        config = Config(ai_api_key="test", github_token="test")
        diffs = [make_file_diff()]
        pr_info = {"title": "Test PR", "author": "dev"}

        result = review_pr(config, diffs, pr_info)
        assert isinstance(result, ReviewResult)
        assert "failed" in result.summary.lower() or "⚠️" in result.summary
