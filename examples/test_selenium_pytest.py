"""
pytest example for Selenium with AI automation.
"""
import time
import pytest
from selenium import webdriver
from autowing.selenium.fixture import create_fixture

from dotenv import load_dotenv


@pytest.fixture(scope="session")
def driver():
    """
    Create and configure Edge WebDriver instance.
    """
    # loading .env file
    load_dotenv()

    driver = webdriver.Edge()
    
    yield driver
    
    driver.quit()


@pytest.fixture
def ai(driver):
    """
    Create an AI-powered Selenium fixture.
    """
    ai_fixture = create_fixture()
    return ai_fixture(driver)


def test_bing_search(ai, driver):
    """
    Test Bing search functionality using AI-driven automation.

    This test demonstrates:
    1. Navigating to Bing
    2. Performing a search
    3. Verifying search results
    """
    # Navigate to Bing
    driver.get("https://cn.bing.com")

    ai.ai_action('搜索输入框输入"playwright"关键字，并回车')
    time.sleep(3)

    items = ai.ai_query('string[], 搜索结果列表中包含"playwright"相关的标题')
    assert len(items) > 1

    # 使用AI断言
    assert ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')


if __name__ == '__main__':
    pytest.main(["test_selenium_pytest.py", "-s"])
