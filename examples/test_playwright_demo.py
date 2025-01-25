import pytest
from playwright.sync_api import Page, sync_playwright
from autowing.playwright.fixture import create_fixture

from dotenv import load_dotenv


@pytest.fixture(scope="session")
def page():
    """playwright fixture"""

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
    print("assert")
    assert ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')