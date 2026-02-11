"""
Unittest example for Selenium with AI automation.
"""
import time
import unittest

from dotenv import load_dotenv
from selenium import webdriver

from autowing.selenium.fixture import create_fixture


class TestBingSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # load .env file
        load_dotenv()
        # Initialize Edge WebDriver
        options = webdriver.ChromeOptions()
        options.add_argument('--disable-web-security')
        options.add_argument('--headless=new')
        cls.driver = webdriver.Chrome(options=options)
        # Create AI fixture
        ai_fixture = create_fixture()
        cls.ai = ai_fixture(cls.driver)

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_01_bing_search(self):
        """
        Test Bing search functionality using AI-driven automation.

        This test demonstrates:
        1. Navigating to Bing
        2. Performing a search
        3. Verifying search results
        """
        self.driver.get("https://cn.bing.com")

        self.ai.ai_action('搜索输入框输入"playwright"关键字，并回车')
        time.sleep(3)

        items = self.ai.ai_query('string[], 搜索结果列表中包含"playwright"相关的标题')

        self.assertGreater(len(items), 1)

        self.assertTrue(
            self.ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')
        )


if __name__ == '__main__':
    unittest.main()
