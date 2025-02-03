"""
pytest example for Playwright with AI automation.
"""
import pytest
from playwright.sync_api import Page, sync_playwright
from autowing.playwright.fixture import create_fixture

from dotenv import load_dotenv


@pytest.fixture(scope="session")
def page():
    """
    playwright fixture
    """
    # loading .env file
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
    """
    ai fixture
    """
    ai_fixture = create_fixture()
    return ai_fixture(page)


def test_bing_search(page: Page, ai):
    """
    Test Bing search functionality using AI-driven automation.
    This test demonstrates:
    1. Navigating to Bing
    2. Performing a search
    3. Verifying search results
    """
    page.goto("https://cn.bing.com")

    ai.ai_action('搜索输入框输入"playwright"关键字，并回车')
    page.wait_for_timeout(3000)

    items = ai.ai_query('string[], 搜索结果列表中包含"playwright"相关的标题')

    assert len(items) > 1

    print("assert")
    assert ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')


if __name__ == '__main__':
    pytest.main(["test_playwright_pytest.py", "-s"])
