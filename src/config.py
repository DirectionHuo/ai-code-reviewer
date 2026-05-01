import os
import logging
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    ai_api_key: str = ""
    ai_api_base: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o"
    ai_api_protocol: str = "auto"  # "auto", "openai", "anthropic"
    github_token: str = ""
    review_language: str = "zh-CN"
    max_files: int = 20
    max_diff_size: int = 500
    ignore_patterns: list[str] = field(default_factory=list)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        ignore_raw = os.getenv("IGNORE_PATTERNS", "")
        ignore_patterns = [p.strip() for p in ignore_raw.split(",") if p.strip()]

        return cls(
            ai_api_key=os.getenv("AI_API_KEY", ""),
            ai_api_base=os.getenv("AI_API_BASE", "https://api.openai.com/v1"),
            ai_model=os.getenv("AI_MODEL", "gpt-4o"),
            ai_api_protocol=os.getenv("AI_API_PROTOCOL", "auto"),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            review_language=os.getenv("REVIEW_LANGUAGE", "zh-CN"),
            max_files=int(os.getenv("MAX_FILES", "20")),
            max_diff_size=int(os.getenv("MAX_DIFF_SIZE", "500")),
            ignore_patterns=ignore_patterns,
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def get_protocol(self) -> str:
        if self.ai_api_protocol != "auto":
            return self.ai_api_protocol
        if "anthropic" in self.ai_api_base.lower():
            return "anthropic"
        return "openai"

    def validate(self) -> list[str]:
        errors = []
        if not self.ai_api_key:
            errors.append("AI_API_KEY is required")
        if not self.github_token:
            errors.append("GITHUB_TOKEN is required")
        return errors

    def setup_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            handlers=[logging.StreamHandler()],
        )


DEFAULT_IGNORE_PATTERNS = [
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "poetry.lock",
    "Pipfile.lock",
    "pnpm-lock.yaml",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.generated.*",
    "*.pb.go",
    "*.pb.cc",
    "*.pb.h",
]


def get_project_root() -> Path:
    return Path(__file__).parent.parent


def get_prompt_path() -> Path:
    return get_project_root() / "prompts" / "review_system_prompt.txt"
