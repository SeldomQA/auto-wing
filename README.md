# auto-wing

![](auto-wing.png)

> auto-wing is a tool that uses LLM to assist automated testing, give your automated testing wings.

auto-wing是一个利用LLM辅助自动化测试的工具, 为你的自动化测试插上AI的翅膀。

### Features

⭐ 支持主流 `playwright`、`selenium`、`appium`库，支持`Web UI`和`App UI`的`AI`操作。

⭐ 支持多模型：`openai`、`deepseek`、`qwen`、`doubao` 和 `gemini`。

⭐ 支持多种操作：`ai_action`、`ai_query`、`ai_assert`。

⭐ 默认支持缓存：首次执行AI任务会被缓存，后续执行相同的任务可以提升效率。

⭐ 无痛的集成到现有自动化项目（`pytest`、`unittest`）中。

## Install

* 支持pip安装，`python >= 3.10`。

```shell
pip install autowing

# playwright [optional]
pip install pytest-playwright

# selenium [optional]
pip install selenium [optional]

# appium [optional]
pip install appium-python-client [optional] 
```

## Setting Env

__方法一__

申请LLM需要的key，在项目的根目录下创建`.env`文件。推荐`qwen`和 `deepseek`，一是便宜，二是方便。

| Provider     | Website                             | Environment Variables（`.env`）                                                                                                      | Notes                |
|--------------|-------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|----------------------|
| **OpenAI**   | https://platform.openai.com/        | `AUTOWING_MODEL_PROVIDER=openai`<br>`OPENAI_API_KEY=sk-proj-abdefghijklmnopqrstwvwxyz0123456789`                                   | 商业模型，功能强大            |
| **DeepSeek** | https://platform.deepseek.com/      | `AUTOWING_MODEL_PROVIDER=deepseek`<br>`DEEPSEEK_API_KEY=sk-abdefghijklmnopqrstwvwxyz0123456789`                                    | **推荐** - 免费额度充足，性价比高 |
| **千问**       | https://bailian.console.aliyun.com/ | `AUTOWING_MODEL_PROVIDER=qwen`<br>`DASHSCOPE_API_KEY=sk-abdefghijklmnopqrstwvwxyz0123456789`                                       | **推荐** - 国内用户友好，响应快  |
| **豆包**       | https://console.volcengine.com/     | `AUTOWING_MODEL_PROVIDER=doubao`<br>`ARK_API_KEY=f61d2846-xxx-xxx-xxxx-xxxxxxxxxxxxx`<br>`DOUBAO_MODEL_NAME=ep-20250207200649-xxx` | 字节跳动出品，中文效果好         |
| **Gemini**   | https://aistudio.google.com/        | `AUTOWING_MODEL_PROVIDER=gemini`<br>`GOOGLE_API_KEY=AIabdefghijklmnopqrstwvwxyz0123456789`                                         | ⚠️ 免费额度有限，建议作为备选     |

__方法二__

> 如果不想使用python-dotenv配置环境变量，可以直接配置环境变量。

```shell
export AUTOWING_MODEL_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-abdefghijklmnopqrstwvwxyz0123456789
```

> 其他LLM模型环境变量同样的方式配置。

## Examples

👉 [查看 examples](./examples)

```python
import pytest
from playwright.sync_api import Page
from autowing.playwright.fixture import create_fixture
from dotenv import load_dotenv


@pytest.fixture
def ai(page):
    """ai fixture"""
    # load .env file config
    load_dotenv()
    ai_fixture = create_fixture()
    return ai_fixture(page)


def test_bing_search(page: Page, ai):
    # 访问必应
    page.goto("https://cn.bing.com")

    # 使用AI执行搜索
    ai.ai_action('搜索输入框输入"playwright"关键字，并回车')
    page.wait_for_timeout(3000)

    # 使用AI查询搜索结果
    items = ai.ai_query('string[], 搜索结果列表中包含"playwright"相关的标题')

    # 验证结果
    assert len(items) > 1

    # 使用AI断言
    assert ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')
```

* 运行日志：

``shell
> pytest test_playwright_pytest.py -s
> ================================================= test session
> starts =================================================
> platform win32 -- Python 3.12.3, pytest-8.3.4, pluggy-1.5.0
> rootdir: D:\github\seldomQA\auto-wing
> configfile: pyproject.toml
> plugins: base-url-2.1.0, playwright-0.6.2
> collected 1 item

test_playwright_pytest.py 2025-02-04 10:00:30.961 | INFO | autowing.playwright.fixture:ai_action:88 - 🪽 AI Action:
搜索输入框输入"playwright"关键字，并回车
2025-02-04 10:00:40.070 | INFO | autowing.playwright.fixture:ai_query:162 - 🪽 AI Query: string[], 搜索结果列表中包 含"
playwright"相关的标题
2025-02-04 10:00:48.954 | DEBUG | autowing.playwright.fixture:ai_query:218 - 📄
Query: ['Playwright 官方文档 | Playwright', 'Playwright - 快速、可靠的端到端测试框架', 'Playwright 中文文档 | Playwright', 'Playwright 入门指南 | Playwright', 'Playwright 测试框架 | Playwright', 'Playwright 教程 | Playwright', 'Playwright 使用指南 | Playwright', 'Playwright 自动化测试工具 | Playwright', 'Playwright 安装与配置 | Playwright', 'Playwright 示例代码 | Playwright']
2025-02-04 10:00:48.954 | INFO | autowing.playwright.fixture:ai_assert:267 - 🪽 AI Assert: 检查搜索结果列表第一条标
题是否包含"playwright"字符串
.

================================================= 1 passed in 27.99s ==================================================

```

## Prompting Tips

__1.提供更详细的描述以及样例__

提供详细描述和示例一直是非常有用的提示词技巧。

错误示例 ❌: `"搜'耳机'"`

正确示例 ✅: `"找到搜索框（搜索框的上方应该有区域切换按钮，如 '国内'， '国际')，输入'耳机'，敲回车"`

错误示例 ❌: `"断言：外卖服务正在正常运行"`

正确示例 ✅: `"断言：界面上有个“外卖服务”的板块，并且标识着“正常”"`

__2.一个 Prompt (指令)只做一件事__

尽管 auto-wing 有自动重规划能力，但仍应保持指令简洁。否则，LLM 的输出可能会变得混乱。指令的长度对 token 消耗的影响几乎可以忽略不计。

错误示例 ❌:`"点击登录按钮，然后点击注册按钮，在表单中输入'test@test.com'作为邮箱，'test'作为密码，然后点击注册按钮"`

正确示例
✅: `将任务分解为三个步骤："点击登录按钮" "点击注册按钮" "在表单中输入'test@test.com'作为邮箱，'test'作为密码，然后点击注册按钮"`

__3.从界面做推断，而不是 DOM 属性或者浏览器状态__

所有传递给 LLM 的数据都是截图和元素坐标。DOM和浏览器 对 LLM 来说几乎是不可见的。因此，务必确保你想提取的信息都在截图中有所体现且能被
LLM “看到”。

正确示例 ✅：`标题是蓝色的`

错误实例 ❌：`标题有个 test-id-size 属性`

错误实例 ❌：`浏览器有两个 tab 开着`

错误实例 ❌：`异步请求已经结束了`

__4.中、英文提示词无影响__

由于大多数 AI 模型可以理解多种语言，所以请随意用你喜欢的语言撰写提示指令。即使提示语言与页面语言不同，通常也是可行的。

### 交流

> 欢迎添加微信，交流和反馈问题。

<div style="display: flex;justify-content: space-between;width: 100%">
    <p><img alt="微信" src="./wechat.jpg" style="width: 200px;height: 100%" ></p>
</div>
