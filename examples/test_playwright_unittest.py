"""
Unittest example for Playwright with AI automation.
"""
import unittest

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from autowing.playwright import create_fixture


class TestBingSearch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # loading .env file
        load_dotenv()
        # Initialize browser
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=False)
        cls.context = cls.browser.new_context()
        cls.page = cls.context.new_page()
        # Create AI fixture
        ai_fixture = create_fixture()
        cls.ai = ai_fixture(cls.page)

    @classmethod
    def tearDownClass(cls):
        cls.context.close()
        cls.browser.close()
        cls.playwright.stop()

    def test_01_bing_search(self):
        """
        Test Bing search functionality using AI-driven automation.
        This test demonstrates:
        1. Navigating to Bing
        2. Performing a search
        3. Verifying search results
        """
        self.page.goto("https://cn.bing.com")

        self.ai.ai_action('搜索输入框输入"playwright"关键字，并回车')
        self.page.wait_for_timeout(3000)

        items = self.ai.ai_query('string[], 搜索结果列表中包含"playwright"相关的标题')

        self.assertGreater(len(items), 1)

        self.assertTrue(
            self.ai.ai_assert('检查搜索结果列表第一条标题是否包含"playwright"字符串')
        )


if __name__ == '__main__':
    unittest.main()
