# Auto-Wing 示例

此目录包含各种示例，演示如何使用 auto-wing 进行 Web 自动化测试。

## 示例文件

| 文件名                                  | 描述                                                    |
|--------------------------------------|-------------------------------------------------------|
| `test_element_markers.py`            | 演示 Playwright 的元素标记注入功能，展示如何向交互元素注入唯一标识符以实现精确定位       |
| `test_selenium_element_markers.py`   | Selenium 版本的元素标记测试，展示 Selenium WebDriver 的相同标记注入功能    |
| `test_playwright_element_markers.py` | Playwright 专用的元素标记注入示例，包含详细演示                         |
| `test_playwright_pytest.py`          | 基础的 Playwright pytest 示例，展示带有搜索功能的 AI 驱动 Web 自动化      |
| `test_playwright_unittest.py`        | Playwright unittest 示例，演示使用 unittest 框架的 AI 驱动 Web 测试 |
| `test_selenium_pytest.py`            | 基础的 Selenium pytest 示例，演示 AI 驱动的 Web 测试功能             |
| `test_selenium_unittest.py`          | Selenium unittest 示例，展示使用 unittest 框架的 AI 自动化         |
| `test_appium_pytest.py`              | Appium pytest 示例，用于带 AI 功能的移动应用测试                     |
| `test_appium_unittest.py`            | Appium unittest 示例，用于移动自动化测试                          |
| `test_playwright_iframes.py`         | 演示如何处理 iframe 元素并在 iframe 内执行 AI 操作（使用 Playwright）    |
| `test_selenium_iframes.py`           | 展示 Selenium WebDriver 的 iframe 处理功能及 AI 集成            |
| `test_intelligent_cache.py`          | 智能缓存管理机制示例                                            |

## 使用方法

每个示例都可以使用 pytest 独立运行：

```bash
# 运行特定示例
pytest test_element_markers.py -v

# 运行所有示例
pytest -v

# 使用详细输出和日志捕获运行
pytest test_playwright_pytest.py -s -v
```

## 框架支持

Auto-wing 支持多种测试框架：

- **Playwright**: 现代浏览器自动化，AI 集成优秀
- **Selenium**: 行业标准的 Web 自动化，浏览器支持广泛
- **Appium**: iOS 和 Android 应用程序的移动应用测试

## 前提条件

运行示例前，请确保：

1. 安装所需的依赖项
2. 设置环境变量（.env 文件）
3. 安装浏览器（用于 Playwright 示例）
4. 设置移动测试环境（用于 Appium 示例）

```bash
# 安装 auto-wing
pip install autowing

# 安装 Playwright 浏览器（如果使用 Playwright 示例）
pip install pytest-playwright
playwright install

# 安装 Selenium 浏览器（如果使用 Selenium 示例）
pip install selenium

# 安装 Appium 依赖项（如果使用 Appium 示例）
pip install Appium-Python-Client

# 使用您的 LLM API 密钥创建 .env 文件
cat .env
# 编辑 .env 文件，填入您的 API 凭据
```

## 环境配置

大多数示例都需要 LLM 提供商的 API 密钥。支持的提供商包括：

- OpenAI
- DeepSeek
- Qwen（阿里云）
- Doubao（火山引擎）
- Gemini（Google）

有关详细的环境设置说明，请参阅主 README。

## 入门指南

1. 从 `test_playwright_pytest.py` 或 `test_selenium_pytest.py` 开始基础使用
2. 通过 `test_element_markers.py` 探索元素标记以实现高级定位
3. 使用 iframe 专用示例尝试 iframe 处理
4. 对于移动测试，使用 Appium 示例
