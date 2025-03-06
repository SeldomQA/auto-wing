import pytest
from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright

from autowing.playwright.fixture import create_fixture


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


def test_baidu_search(page: Page, ai):
    page.goto("https://sahitest.com/demo/iframesTest.htm")

    iframe = page.frame_locator("body > iframe")

    ai.ai_action('点击"Link Test"链接', iframe)

    page.wait_for_timeout(2000)

    ai.ai_query('检查页面是否包含"linkByContent"字符串')


if __name__ == '__main__':
    pytest.main(["test_playwright_iframes.py", "-s"])
