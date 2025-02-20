# auto-wing

![](auto-wing.png)

> auto-wing is a tool that uses LLM to assist automated testing, give your automated testing wings.

auto-wing是一个利用LLM辅助自动化测试的工具, 为你的自动化测试插上翅膀。

### Features

⭐ 集成 `playwright`、`selenium`、`appium`，支持`Web UI`和`App UI`的`AI`操作。

⭐ 支持多模型：`openai`、`deepseek`、`qwen` 和 `doubao`。

⭐ 支持多种操作：`ai_action`、`ai_query`、`ai_assert`。

⭐ 无痛的集成到现有自动化项目（`pytest`、`unittest`）中。

## Install

* 支持pip安装，`python = "^3.9"`。

```shell
pip install autowing
```

## Setting Env

__方法一__

申请LLM需要的key，在项目的根目录下创建`.env`文件。推荐`qwen`和 `deepseek`，一是便宜，二是方便。

* openai: https://platform.openai.com/

```ini
#.env
AUTOWING_MODEL_PROVIDER = openai
OPENAI_API_KEY = =sk-proj-abdefghijklmnopqrstwvwxyz0123456789
```

* DeepSeek: https://platform.deepseek.com/

```ini
#.env
AUTOWING_MODEL_PROVIDER = deepseek
DEEPSEEK_API_KEY = sk-abdefghijklmnopqrstwvwxyz0123456789
```

* 阿里云百练（千问）：https://bailian.console.aliyun.com/

```ini
#.env
AUTOWING_MODEL_PROVIDER = qwen
DASHSCOPE_API_KEY = sk-abdefghijklmnopqrstwvwxyz0123456789
```

* 火山方舟（豆包）：https://console.volcengine.com/

```shell
#.env
AUTOWING_MODEL_PROVIDER=doubao
ARK_API_KEY=f61d2846-xxx-xxx-xxxx-xxxxxxxxxxxxx
DOUBAO_MODEL_NAME=ep-20250207200649-xxx
```

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
from playwright.sync_api import Page, sync_playwright
from autowing.playwright.fixture import create_fixture
from dotenv import load_dotenv


@pytest.fixture(scope="session")
def page():
    """playwright page fixture"""
    # load .env file config
    load_dotenv()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        yield page
        context.close()
        browser.close()


@pytest.fixture
def ai(page):
    """ai fixture"""
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

```shell
> pytest test_playwright_pytest.py -s
================================================= test session starts =================================================
platform win32 -- Python 3.12.3, pytest-8.3.4, pluggy-1.5.0
rootdir: D:\github\seldomQA\auto-wing
configfile: pyproject.toml
plugins: base-url-2.1.0, playwright-0.6.2
collected 1 item

test_playwright_pytest.py 2025-02-04 10:00:30.961 | INFO     | autowing.playwright.fixture:ai_action:88 - 🪽 AI Action: 搜索输入框输入"playwright"关键字，并回车
2025-02-04 10:00:40.070 | INFO     | autowing.playwright.fixture:ai_query:162 - 🪽 AI Query: string[], 搜索结果列表中包 含"playwright"相关的标题
2025-02-04 10:00:48.954 | DEBUG    | autowing.playwright.fixture:ai_query:218 - 📄 Query: ['Playwright 官方文档 | Playwright', 'Playwright - 快速、可靠的端到端测试框架', 'Playwright 中文文档 | Playwright', 'Playwright 入门指南 | Playwright', 'Playwright 测试框架 | Playwright', 'Playwright 教程 | Playwright', 'Playwright 使用指南 | Playwright', 'Playwright 自动化测试工具 | Playwright', 'Playwright 安装与配置 | Playwright', 'Playwright 示例代码 | Playwright']
2025-02-04 10:00:48.954 | INFO     | autowing.playwright.fixture:ai_assert:267 - 🪽 AI Assert: 检查搜索结果列表第一条标 题是否包含"playwright"字符串
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
