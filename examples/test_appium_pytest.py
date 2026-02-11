import time

import pytest
from appium import webdriver
from appium.options.android import UiAutomator2Options
from dotenv import load_dotenv

from autowing.appium import create_fixture


@pytest.fixture(scope="function")
def driver():
    """
    Create and configure Edge WebDriver instance.
    """
    # loading .env file
    load_dotenv()

    capabilities = {
        'deviceName': 'MDX0220413011925',
        'automationName': 'UiAutomator2',
        'platformName': 'Android',
        'appPackage': 'com.microsoft.bing',
        'appActivity': 'com.microsoft.sapphire.app.main.MainSapphireActivity',
        'noReset': True,
    }
    options = UiAutomator2Options().load_capabilities(capabilities)
    driver = webdriver.Remote(command_executor="http://127.0.0.1:4723", options=options)

    yield driver

    driver.quit()


@pytest.fixture
def ai(driver):
    """
    Create an AI-powered Selenium fixture.
    """
    ai_fixture = create_fixture()
    return ai_fixture(driver, "Android")


def test_bing_search(ai, driver):
    """
    test bing App search
    """
    ai.ai_action('点击搜索框，然后输入"auto-wing"关键字，然后回车搜索')
    time.sleep(3)

    items = ai.ai_query('string[], 搜索结果列表中包含"auto-wing"相关的标题')
    assert len(items) > 1

    ai.ai_assert('检查搜索结果列表第一条标题是否包含"auto-wing"字符串')


if __name__ == '__main__':
    pytest.main(["test_appium_pytest.py", "-s"])
