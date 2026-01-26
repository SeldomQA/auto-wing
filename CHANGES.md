### 0.6.2

* 更新安装依赖库，减少比不要的安装。
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
