import json
import logging
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)


class GitHubClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _request(
        self, method: str, endpoint: str, **kwargs: Any
    ) -> requests.Response:
        url = f"{self.base_url}{endpoint}"
        for attempt in range(3):
            try:
                resp = self.session.request(method, url, **kwargs)

                if resp.status_code == 403:
                    remaining = resp.headers.get("X-RateLimit-Remaining", "0")
                    if remaining == "0":
                        reset_time = int(resp.headers.get("X-RateLimit-Reset", "0"))
                        wait = max(reset_time - int(time.time()), 1)
                        logger.warning("Rate limited, waiting %ds", wait)
                        time.sleep(min(wait, 60))
                        continue

                resp.raise_for_status()
                return resp
            except requests.RequestException as e:
                if attempt < 2:
                    wait = 2 ** attempt
                    logger.warning(
                        "Request failed (attempt %d/3): %s, retrying in %ds",
                        attempt + 1, e, wait,
                    )
                    time.sleep(wait)
                else:
                    logger.error("Request failed after 3 attempts: %s", e)
                    raise
        raise RuntimeError("Unreachable")

    def get_pr_info(self, repo: str, pr_number: int) -> dict:
        resp = self._request("GET", f"/repos/{repo}/pulls/{pr_number}")
        data = resp.json()
        return {
            "title": data.get("title", ""),
            "body": data.get("body", ""),
            "author": data.get("user", {}).get("login", ""),
            "base_branch": data.get("base", {}).get("ref", ""),
            "head_branch": data.get("head", {}).get("ref", ""),
            "head_sha": data.get("head", {}).get("sha", ""),
        }

    def get_pr_diff(self, repo: str, pr_number: int) -> str:
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        resp = self.session.get(
            url, headers={"Accept": "application/vnd.github.v3.diff"}
        )
        resp.raise_for_status()
        return resp.text

    def get_pr_files(self, repo: str, pr_number: int) -> list[dict]:
        files: list[dict] = []
        page = 1
        while True:
            resp = self._request(
                "GET",
                f"/repos/{repo}/pulls/{pr_number}/files",
                params={"per_page": 100, "page": page},
            )
            page_files = resp.json()
            if not page_files:
                break
            files.extend(page_files)
            page += 1
        return files

    def submit_review(
        self,
        repo: str,
        pr_number: int,
        comments: list[dict],
        summary: str,
        event: str = "COMMENT",
        commit_sha: str = "",
    ) -> None:
        review_comments = []
        for c in comments:
            comment: dict[str, Any] = {
                "path": c["path"],
                "body": c["body"],
            }
            if "line" in c and c["line"]:
                comment["line"] = c["line"]
                comment["side"] = "RIGHT"
            elif "position" in c and c["position"]:
                comment["position"] = c["position"]
            else:
                continue
            review_comments.append(comment)

        body: dict[str, Any] = {
            "body": summary,
            "event": event,
        }
        if commit_sha:
            body["commit_id"] = commit_sha
        if review_comments:
            body["comments"] = review_comments

        try:
            self._request(
                "POST",
                f"/repos/{repo}/pulls/{pr_number}/reviews",
                json=body,
            )
            logger.info(
                "Review submitted: %s with %d inline comments",
                event, len(review_comments),
            )
        except requests.RequestException as e:
            logger.error("Failed to submit review: %s", e)
            if review_comments:
                logger.info("Retrying with summary only (no inline comments)")
                fallback_body: dict[str, Any] = {
                    "body": summary,
                    "event": "COMMENT",
                }
                if commit_sha:
                    fallback_body["commit_id"] = commit_sha
                try:
                    self._request(
                        "POST",
                        f"/repos/{repo}/pulls/{pr_number}/reviews",
                        json=fallback_body,
                    )
                    logger.info("Fallback review (summary only) submitted")
                except requests.RequestException as e2:
                    logger.error("Fallback review also failed: %s", e2)
