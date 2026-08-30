# 环境变量配置指南

auto-wing 的所有行为开关与 LLM 配置均通过环境变量控制。推荐将
[examples/.env.example](../examples/.env.example) 复制为项目根目录（或 `examples/`）
下的 `.env` 文件，配合 `python-dotenv` 加载：

```python
from dotenv import load_dotenv

load_dotenv()
```

> ⚠️ `.env` 中包含 API Key，切勿提交到版本库（`.gitignore` 已默认忽略）。

---

## 一、LLM 提供商选择

| 变量 | 说明 | 默认值 |
|---|---|---|
| `AUTOWING_MODEL_PROVIDER` | LLM 提供商：`openai` / `deepseek` / `qwen` / `doubao` / `gemini` / `kimi` | `deepseek` |

推荐 `qwen` 和 `deepseek`：一是便宜，二是方便。

## 二、各提供商配置

每家提供商统一三类配置：**API Key（必填）**、**模型名（可选，豆包必填）**、**API 端点（可选）**。

### DeepSeek（https://platform.deepseek.com/）

| 变量 | 必填 | 默认值 |
|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ | — |
| `DEEPSEEK_MODEL_NAME` | ❌ | `deepseek-chat` |
| `DEEPSEEK_BASE_URL` | ❌ | `https://api.deepseek.com` |

### 千问 Qwen（阿里云百炼：https://bailian.console.aliyun.com/）

| 变量 | 必填 | 默认值 |
|---|---|---|
| `DASHSCOPE_API_KEY` | ✅ | — |
| `QWEN_MODEL_NAME` | ❌ | `qwen3-max` |
| `QWEN_BASE_URL` | ❌ | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

> 开启视觉模式（`AUTOWING_VISION=true`）时，建议将模型切换为视觉模型，
> 例如 `QWEN_MODEL_NAME=qwen3-vl-plus`。

### OpenAI（https://platform.openai.com/）

| 变量 | 必填 | 默认值 |
|---|---|---|
| `OPENAI_API_KEY` | ✅ | — |
| `OPENAI_MODEL_NAME` | ❌ | `gpt-4o-2024-08-06` |
| `OPENAI_BASE_URL` | ❌ | `https://api.openai.com/v1` |

### 豆包 Doubao（火山方舟：https://console.volcengine.com/）

| 变量 | 必填 | 默认值 |
|---|---|---|
| `ARK_API_KEY` | ✅ | — |
| `DOUBAO_MODEL_NAME` | ✅（方舟平台创建的推理接入点，如 `ep-20250207200649-xxx`） | — |
| `DOUBAO_BASE_URL` | ❌ | `https://ark.cn-beijing.volces.com/api/v3` |

### Gemini（Google AI Studio：https://aistudio.google.com/）

| 变量 | 必填 | 默认值 |
|---|---|---|
| `GOOGLE_API_KEY` | ✅ | — |
| `GEMINI_MODEL_NAME` | ❌ | `gemini-2.0-flash` |

### Kimi（月之暗面：https://platform.moonshot.cn/）

| 变量 | 必填 | 默认值 |
|---|---|---|
| `KIMI_API_KEY`（兼容官方的 `MOONSHOT_API_KEY`，前者优先） | ✅ | — |
| `KIMI_MODEL_NAME` | ❌ | `kimi-latest` |
| `KIMI_BASE_URL` | ❌ | `https://api.moonshot.cn/v1` |

> 历史配置兼容：早期版本中 openai / qwen / gemini 的模型名读取 `MIDSCENE_MODEL_NAME`，
> 该变量仍作为回退生效，但新配置请使用 `<PROVIDER>_MODEL_NAME`。

## 三、auto-wing 运行配置（全部可选）

| 变量 | 默认值 | 说明 |
|---|---|---|
| `AUTOWING_VISION` | `false` | 视觉模式：每次 AI 调用附带页面截图，供视觉模型定位元素；模型不支持图片时自动降级为纯文本模式 |
| `AUTOWING_CACHE_DIR` | `.auto-wing/cache` | 智能缓存目录；同一目录下所有 fixture 共享同一个缓存管理器，跨用例命中 |
| `AUTOWING_MAX_RETRIES` | `2` | `ai_action` 失败重试/重规划次数：LLM 返回非法 JSON 或动作执行失败时，携带错误信息重新规划 |
| `AUTOWING_ACTION_TIMEOUT` | `30` | 单个元素操作超时（秒），统一约束 Playwright 元素操作与 Selenium / Appium 的等待 |
| `AUTOWING_DEBUG` | `false` | 打印发送给 LLM 的完整 prompt 与原始响应，排查问题用 |
| `AUTOWING_SCREENSHOT_DIR` | `.auto-wing/screenshots` | 动作失败时的自动截图保存目录 |

调试产物说明：动作失败时除截图外，还会向缓存目录旁的 `trace.jsonl` 追加执行轨迹
（时间、指令、错误、截图路径），便于复盘。

## 四、最小配置示例

以 DeepSeek 为例，最简 `.env` 只需两行：

```shell
AUTOWING_MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

也可以不使用 `python-dotenv`，直接配置系统环境变量：

```shell
export AUTOWING_MODEL_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```
