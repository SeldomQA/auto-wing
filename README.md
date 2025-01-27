# auto-wing

![](auto-wing.png)

> auto-wing is a tool that uses LLM to assist automated testing, give your automated testing wings.

auto-wing是一个利用LLM辅助自动化测试的工具, 为你的自动化测试插上翅膀。


### Features

⭐ 支持多种操作：`ai_action`、`ai_query`、`ai_assert`。

⭐ 支持多模型：`openai`、`qwen` 和 `deepseek`。

⭐ 支持 `playwright`、`selenium`。

⭐ 方便的和现有自动化项目（`pytest`、`unittest`）集成。

### Install

```shell
pip install autowing
```

### setting env

__方法一__

申请LLM需要的key，在项目的根目录下创建`.env`文件。推荐`qwen`和 `deepseek`，一是便宜，二是方便。

* openai: https://platform.openai.com/

```ini
#.env
AUTOWING_MODEL_PROVIDER=openai
OPENAI_API_KEY==sk-proj-abdefghijklmnopqrstwvwxyz0123456789
```

* DeepSeek: https://platform.deepseek.com/

```ini
#.env
AUTOWING_MODEL_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-abdefghijklmnopqrstwvwxyz0123456789
```

* 阿里云百练：https://bailian.console.aliyun.com/

```ini
#.env
AUTOWING_MODEL_PROVIDER=qwen
DASHSCOPE_API_KEY=sk-abdefghijklmnopqrstwvwxyz0123456789
```

__方法二__

> 如果不想使用python-dotenv配置环境变量，可以直接配置环境变量。

```shell
export AUTOWING_MODEL_PROVIDER=deepseek
export DEEPSEEK_API_KEY=sk-abdefghijklmnopqrstwvwxyz0123456789
```

### 使用

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
    print("query", items)

    # 验证结果
    assert len(items) > 1

    # 使用AI断言
    assert ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')
```

### 交流

> 欢迎添加微信，交流和反馈问题。

<div style="display: flex;justify-content: space-between;width: 100%">
    <p><img alt="微信" src="./wechat.jpg" style="width: 200px;height: 100%" ></p>
</div>
