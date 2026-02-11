import time

import pytest
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By

from autowing.selenium.fixture import create_fixture


@pytest.fixture(scope="session")
def driver():
    """
    Create and configure Edge WebDriver instance.
    """

    load_dotenv()

    options = webdriver.ChromeOptions()
    options.add_argument('--disable-web-security')
    options.add_argument('--headless=new')
    driver = webdriver.Chrome(options=options)

    yield driver

    driver.quit()


@pytest.fixture
def ai(driver):
    """
    Create an AI-powered Selenium fixture.
    """
    ai_fixture = create_fixture()
    return ai_fixture(driver)


def test_iframes(ai, driver):
    driver.get("https://sahitest.com/demo/iframesTest.htm")

    iframe = driver.find_element(By.XPATH, "/html/body/iframe")
    driver.switch_to.frame(iframe)

    ai.ai_action('点击"Link Test"链接')

    time.sleep(2)

    ai.ai_query('检查页面是否包含"linkByContent"字符串')


if __name__ == '__main__':
    pytest.main(["test_selenium_iframes.py", "-s"])
