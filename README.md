# 🤖 AI Code Reviewer

基于 AI 的 GitHub Pull Request 自动代码审查工具。当 PR 提交或更新时，自动触发 AI 对代码变更进行多维度审查，并将审查意见提交回 PR。

## 功能特性

- **多维度审查**：Bug 风险、安全性、性能、代码风格、最佳实践
- **精准定位**：审查意见精确到文件和行号，以 inline comment 形式展示
- **风险评级**：自动评估变更风险等级（Low / Medium / High / Critical）
- **智能过滤**：自动跳过 lock 文件、二进制文件、自动生成文件等
- **大文件处理**：大 diff 自动分块审查，避免超出上下文限制
- **多模型支持**：兼容 OpenAI、Claude、DeepSeek、MiMo 等 OpenAI 兼容接口
- **双语支持**：审查意见支持中文和英文
- **容错机制**：API 调用失败自动重试，单文件失败不影响整体审查

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将本仓库 fork 到你的 GitHub 账号下。

### 2. 配置 Secrets

进入你 fork 后的仓库，依次打开 **Settings → Secrets and variables → Actions**，添加以下 Secrets：

| Secret 名称 | 必填 | 说明 |
|-------------|------|------|
| `AI_API_KEY` | ✅ | AI 服务的 API Key |
| `AI_API_BASE` | ❌ | API 地址，默认 `https://api.openai.com/v1` |

### 3. 配置 Variables（可选）

在 **Settings → Secrets and variables → Actions → Variables** 中配置：

| Variable 名称 | 默认值 | 说明 |
|---------------|--------|------|
| `AI_MODEL` | `gpt-4o` | 模型名称 |
| `REVIEW_LANGUAGE` | `zh-CN` | 审查语言（`zh-CN` 或 `en`） |
| `MAX_FILES` | `20` | 最大审查文件数 |
| `IGNORE_PATTERNS` | 空 | 自定义忽略文件模式，逗号分隔 |

### 4. 测试

创建一个新的 PR，等待 GitHub Actions 运行完成，即可在 PR 中看到 AI 的审查意见。

## 配置说明

所有配置通过环境变量设置：

| 环境变量 | 类型 | 默认值 | 说明 |
|---------|------|--------|------|
| `AI_API_KEY` | string | - | AI API 密钥（必填） |
| `AI_API_BASE` | string | `https://api.openai.com/v1` | API 基础 URL |
| `AI_MODEL` | string | `gpt-4o` | 模型名称 |
| `GITHUB_TOKEN` | string | - | GitHub Token（Actions 自动提供） |
| `REVIEW_LANGUAGE` | string | `zh-CN` | 审查意见语言 |
| `MAX_FILES` | int | `20` | 单次最大审查文件数 |
| `MAX_DIFF_SIZE` | int | `500` | 单文件最大 diff 行数 |
| `IGNORE_PATTERNS` | string | 空 | 额外忽略文件模式，逗号分隔 |
| `LOG_LEVEL` | string | `INFO` | 日志级别 |

## 支持的 AI 服务

本项目使用 OpenAI 兼容接口，以下服务已验证可用：

| 服务商 | AI_API_BASE | AI_MODEL | 说明 |
|--------|-------------|----------|------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` | 默认配置 |
| Claude (via proxy) | 你的代理地址 | `claude-sonnet-4-6` | 需要 OpenAI 兼容代理 |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` | 性价比高 |
| MiMo | 对应 API 地址 | 对应模型名 | 按服务商文档配置 |

### 配置示例

**使用 DeepSeek：**
```
AI_API_KEY=your-deepseek-key
AI_API_BASE=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat
```

## 本地开发

```bash
# 克隆仓库
git clone https://github.com/your-username/ai-code-reviewer.git
cd ai-code-reviewer

# 安装依赖
pip install -r requirements.txt

# 复制环境变量模板
cp .env.example .env
# 编辑 .env 填入你的配置

# 运行测试
pytest tests/ -v

# 本地运行（需设置环境变量）
export GITHUB_REPOSITORY=owner/repo
export PR_NUMBER=1
export AI_API_KEY=your-key
export GITHUB_TOKEN=your-token
python -m src.main
```

## 审查效果示例

<!-- 审查截图占位 -->

*提交 PR 后，AI 会自动进行代码审查并提交 review：*

> 截图待补充

## 项目结构

```
ai-code-reviewer/
├── .github/workflows/
│   └── code-review.yml          # GitHub Actions 工作流
├── src/
│   ├── main.py                  # 入口
│   ├── github_client.py         # GitHub API 封装
│   ├── ai_reviewer.py           # AI 审查引擎
│   ├── diff_parser.py           # diff 解析器
│   ├── review_formatter.py      # 审查结果格式化
│   └── config.py                # 配置管理
├── prompts/
│   └── review_system_prompt.txt # System Prompt
├── tests/                       # 单元测试
├── examples/                    # 示例文件
├── requirements.txt
└── .env.example
```

## License

MIT
