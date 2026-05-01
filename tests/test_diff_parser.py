import pytest
from pathlib import Path

from src.diff_parser import (
    DiffHunk,
    FileDiff,
    count_changes,
    parse_patch,
    parse_pr_files,
    should_ignore_file,
)


SAMPLE_PATCH = """\
@@ -0,0 +1,35 @@
+import hashlib
+import sqlite3
+
+DB_PASSWORD = "super_secret_123"
+
+def authenticate(username, password):
+    conn = sqlite3.connect("users.db")"""


MULTI_HUNK_PATCH = """\
@@ -10,7 +10,7 @@ def calculate_total(items):
     total = 0
     for item in items:
-        total += item.price
+        total += item.price * item.quantity
     return total
@@ -20,3 +20,15 @@ def format_currency(amount):
     return f"${amount:.2f}"
+
+def parse_config(config_str):
+    import yaml
+    return yaml.load(config_str)"""


class TestParsePatch:
    def test_single_hunk(self):
        hunks = parse_patch(SAMPLE_PATCH)
        assert len(hunks) == 1
        assert hunks[0].start_line == 1
        assert hunks[0].end_line == 7

    def test_multi_hunk(self):
        hunks = parse_patch(MULTI_HUNK_PATCH)
        assert len(hunks) == 2
        assert hunks[0].start_line == 10
        assert hunks[1].start_line == 20

    def test_empty_patch(self):
        hunks = parse_patch("")
        assert hunks == []

    def test_hunk_content_preserved(self):
        hunks = parse_patch(SAMPLE_PATCH)
        assert "import hashlib" in hunks[0].content
        assert "sqlite3" in hunks[0].content


class TestCountChanges:
    def test_additions_only(self):
        patch = "+line1\n+line2\n+line3"
        adds, dels = count_changes(patch)
        assert adds == 3
        assert dels == 0

    def test_mixed_changes(self):
        patch = "+added\n-removed\n context\n+added2"
        adds, dels = count_changes(patch)
        assert adds == 2
        assert dels == 1

    def test_ignores_file_markers(self):
        patch = "--- a/file.py\n+++ b/file.py\n+line"
        adds, dels = count_changes(patch)
        assert adds == 1
        assert dels == 0


class TestShouldIgnoreFile:
    def test_lock_files(self):
        assert should_ignore_file("package-lock.json")
        assert should_ignore_file("yarn.lock")
        assert should_ignore_file("poetry.lock")

    def test_minified_files(self):
        assert should_ignore_file("app.min.js")
        assert should_ignore_file("styles.min.css")

    def test_map_files(self):
        assert should_ignore_file("bundle.js.map")

    def test_normal_files(self):
        assert not should_ignore_file("src/main.py")
        assert not should_ignore_file("README.md")
        assert not should_ignore_file("src/utils.js")

    def test_custom_patterns(self):
        assert should_ignore_file("test.generated.ts", ["*.generated.*"])
        assert not should_ignore_file("test.ts", ["*.generated.*"])

    def test_path_with_directories(self):
        assert should_ignore_file("frontend/dist/app.min.js")


class TestParsePrFiles:
    def test_basic_parsing(self):
        files = [
            {
                "filename": "src/main.py",
                "status": "modified",
                "patch": "@@ -1,3 +1,4 @@\n context\n+added line\n more context",
            }
        ]
        result = parse_pr_files(files)
        assert len(result) == 1
        assert result[0].filename == "src/main.py"
        assert result[0].status == "modified"
        assert result[0].additions == 1
        assert result[0].deletions == 0

    def test_ignores_lock_files(self):
        files = [
            {"filename": "package-lock.json", "status": "modified", "patch": "+x"},
            {"filename": "src/app.js", "status": "modified", "patch": "+y"},
        ]
        result = parse_pr_files(files)
        assert len(result) == 1
        assert result[0].filename == "src/app.js"

    def test_skips_binary_files(self):
        files = [
            {"filename": "image.png", "status": "added", "patch": ""},
        ]
        result = parse_pr_files(files)
        assert len(result) == 0

    def test_max_files_limit(self):
        files = [
            {"filename": f"file{i}.py", "status": "modified", "patch": "+line"}
            for i in range(30)
        ]
        result = parse_pr_files(files, max_files=5)
        assert len(result) == 5

    def test_with_sample_diff(self):
        sample_path = Path(__file__).parent.parent / "examples" / "sample_diff.patch"
        if sample_path.exists():
            content = sample_path.read_text(encoding="utf-8")
            assert "authenticate" in content
            assert "calculate_total" in content
