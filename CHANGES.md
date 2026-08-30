### 0.8.1

* 功能：增加 `kimi`（月之暗面）模型支持，兼容官方 `MOONSHOT_API_KEY` 环境变量。
* 功能：各提供商模型版本抽成可配置项：`OPENAI_MODEL_NAME` / `QWEN_MODEL_NAME` / `GEMINI_MODEL_NAME`（保留旧变量
  `MIDSCENE_MODEL_NAME` 回退兼容），新增 `QWEN_BASE_URL`。
* 优化：新增 `examples/.env.example` 配置模板（提供商 KEY / 模型名 / 端点 + 运行配置全量注释）。

### 0.8.0

* 功能：增加视觉能力，`AUTOWING_VISION` 环境变量 / `enable_vision()` 开关，截图随请求传给视觉模型，不支持时自动降级为纯文本模式。
* 功能：`ai_action()` 动作集扩展，新增 `select`（下拉选择）、`hover`、`check`/`uncheck`、`scroll`、`upload`。
* 功能：`ai_action()` 失败重试与重规划，失败后淘汰失效缓存并携带错误信息重新规划（`AUTOWING_MAX_RETRIES` 可配置，默认 2
  次），非法 JSON 响应自动反馈重试。
* 功能：支持 iframe 与 Shadow DOM：标记注入/元素采集覆盖同源 iframe 与 open Shadow DOM；Playwright
  `ai_action(prompt, frame=...)` 支持指定 frame。
* 功能：调试辅助能力：`AUTOWING_DEBUG` 打印完整 prompt/响应；动作失败自动截图；执行轨迹记录 `.auto-wing/trace.jsonl`；
  `AUTOWING_ACTION_TIMEOUT` 统一操作超时（默认 30 秒）。
* 功能：三驱动构造器支持注入自定义 LLM 客户端（`llm_client=` 参数），便于离线 Mock 测试。
* 优化：`IntelligentCacheManager` 进程级共享（按 `AUTOWING_CACHE_DIR` 复用），跨用例共享缓存提升命中率。
* 优化：`ai_query()`/`ai_assert()` 实现收敛至基类，三端行为对齐。
* 修复：缓存指令定位失败未淘汰导致的反复命中失效缓存。
* 修复：Gemini 客户端图片传入方式（改为 `inline_data`）。
* 修复：`ai_assert()` 三端元素上下文不一致；异常分支变量未定义掩盖原始错误。
* 修复：`[text() = 'x']` 带空白谓词在 Playwright 端转换失效；`object[]` 格式提示返回 `None`。
* 工程：建立 `tests/` 单元/集成测试套件（135 个用例，浏览器/模型依赖优雅跳过）；引入 `ruff`/`mypy` 质量门禁；清理仓库历史遗留调试脚本。

### 0.7.0

* Web端操作增加页面元素注入定位属性，提升定位的稳定性。
* 实现智能缓存管理机制，提升缓存命中率。
* 增加`gemini`模型的支持。

### 0.6.2

* 更新安装依赖库，减少比不必要的安装。
* 删除打印信息。
* 更新qwen默认模型，使用最新`qwen-max`。

### 0.6.1

* 支持AI操作文本链接。
* appium升级`>5.1`。
* 更新qwen默认模型，使用最新`qwen3`。

### 0.6.0

* 增加默认缓存功能，减少不必要的LLM调用，增加速度。
* 移动端支持iOS❕。
* 更新qwen默认模型，使用最新`qwen2.5`。

### 0.5.1

* 识别更多的页面元素。
* CSS选择器优化提示词，用于识别包含`$`符号的ID属性。
* `playwright`/`selenium` 分别支持表单操作。
* 移除`prompt`中无效信息，节省`tokens`使用。
* LLM客户端代码优化。

### 0.5.0

* 功能：增加 `ai_function_case()`, 识别页面元素生成功能用例。
* 功能：增加appium依赖，支持App端的AI操作。

### 0.4.0

* 功能：增加 `doubao`支持。

### 0.3.0

* 增加日志功能，调用相关API显示日志。
* 优化fixture相关代码。
* python版本要求`>=3.9`(最新selenium版本要求)。

### 0.2.2

* 优化：`ai_query()`、`ai_assert()`识别速度和格式兼容性。

### 0.2.1

* 优化：python版本要求改为`>=3.8`。

### 0.2.0

* 功能：增加 `openai`支持。

### 0.1.0

* 功能：
    * 支持LLM: `qwen`、`deepseek`。
    * 提供操作：`ai_action()`、`ai_query()`、`ai_assert()`。
    * 支持测试库： `playwright`、`selenium`等。
