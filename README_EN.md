# 🤖 AI Code Reviewer

An AI-powered automatic code review tool for GitHub Pull Requests. Automatically triggers AI to review code changes across multiple dimensions when a PR is created or updated, and posts review comments directly on the PR.

## Features

- **Multi-dimensional review**: Bug risk, security, performance, code style, best practices
- **Precise positioning**: Review comments pinpointed to exact file and line number as inline comments
- **Risk assessment**: Automatic risk level rating (Low / Medium / High / Critical)
- **Smart filtering**: Auto-skips lock files, binary files, generated files, etc.
- **Large file handling**: Automatically chunks large diffs to stay within context limits
- **Multi-model support**: Compatible with OpenAI, Claude, DeepSeek, MiMo and other OpenAI-compatible APIs
- **Bilingual**: Review comments in Chinese or English
- **Fault tolerance**: Auto-retry on API failures; single file failure doesn't block the review

## Quick Start

### 1. Fork this repository

Click the **Fork** button in the top-right corner.

### 2. Configure Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Required | Description |
|--------|----------|-------------|
| `AI_API_KEY` | ✅ | Your AI service API key |
| `AI_API_BASE` | ❌ | API base URL, defaults to `https://api.openai.com/v1` |

### 3. Configure Variables (Optional)

In **Settings → Secrets and variables → Actions → Variables**:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_MODEL` | `gpt-4o` | Model name |
| `REVIEW_LANGUAGE` | `zh-CN` | Review language (`zh-CN` or `en`) |
| `MAX_FILES` | `20` | Max files to review |
| `IGNORE_PATTERNS` | empty | Custom ignore patterns, comma-separated |

### 4. Test

Create a new PR and wait for GitHub Actions to complete. You'll see AI review comments on the PR.

## Configuration

All settings are configured via environment variables:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `AI_API_KEY` | string | - | AI API key (required) |
| `AI_API_BASE` | string | `https://api.openai.com/v1` | API base URL |
| `AI_MODEL` | string | `gpt-4o` | Model name |
| `GITHUB_TOKEN` | string | - | GitHub token (auto-provided by Actions) |
| `REVIEW_LANGUAGE` | string | `zh-CN` | Review comment language |
| `MAX_FILES` | int | `20` | Max files to review per PR |
| `MAX_DIFF_SIZE` | int | `500` | Max diff lines per file |
| `IGNORE_PATTERNS` | string | empty | Additional ignore patterns, comma-separated |
| `LOG_LEVEL` | string | `INFO` | Log level |

## Supported AI Services

This project uses the OpenAI-compatible API interface:

| Provider | AI_API_BASE | AI_MODEL | Notes |
|----------|-------------|----------|-------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` | Default |
| Claude (via proxy) | Your proxy URL | `claude-sonnet-4-6` | Requires OpenAI-compatible proxy |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | Cost-effective |
| MiMo | Provider API URL | Provider model | Configure per provider docs |

## Local Development

```bash
# Clone the repo
git clone https://github.com/your-username/ai-code-reviewer.git
cd ai-code-reviewer

# Install dependencies
pip install -r requirements.txt

# Copy env template
cp .env.example .env
# Edit .env with your configuration

# Run tests
pytest tests/ -v

# Run locally (requires env vars)
export GITHUB_REPOSITORY=owner/repo
export PR_NUMBER=1
export AI_API_KEY=your-key
export GITHUB_TOKEN=your-token
python -m src.main
```

## Example Output

<!-- Screenshot placeholder -->

*After submitting a PR, the AI automatically reviews and posts comments:*

> Screenshots coming soon

## Project Structure

```
ai-code-reviewer/
├── .github/workflows/
│   └── code-review.yml          # GitHub Actions workflow
├── src/
│   ├── main.py                  # Entry point
│   ├── github_client.py         # GitHub API wrapper
│   ├── ai_reviewer.py           # AI review engine
│   ├── diff_parser.py           # Diff parser
│   ├── review_formatter.py      # Review result formatter
│   └── config.py                # Configuration
├── prompts/
│   └── review_system_prompt.txt # System prompt
├── tests/                       # Unit tests
├── examples/                    # Example files
├── requirements.txt
└── .env.example
```

## License

MIT
