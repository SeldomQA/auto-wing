import time
import unittest

from appium import webdriver
from appium.options.android import UiAutomator2Options
from dotenv import load_dotenv

from autowing.appium.fixture import create_fixture


class TestBingApp(unittest.TestCase):
    """
    Test Bing APP
    """

    @classmethod
    def setUpClass(cls):
        load_dotenv()

    def setUp(self):
        capabilities = {
            'deviceName': 'MDX0220413011925',
            'automationName': 'UiAutomator2',
            'platformName': 'Android',
            'appPackage': 'com.microsoft.bing',
            'appActivity': 'com.microsoft.sapphire.app.main.MainSapphireActivity',
            'noReset': True,
        }
        options = UiAutomator2Options().load_capabilities(capabilities)
        self.driver = webdriver.Remote(command_executor="http://127.0.0.1:4723", options=options)

        ai_fixture = create_fixture()
        self.ai = ai_fixture(self.driver)

    def tearDown(self):
        self.driver.quit()

    def test_bing_search(self):
        """
        test bing App search
        """
        self.ai.ai_action('点击搜索框，然后输入"auto-wing"关键字，然后回车搜索')
        time.sleep(3)

        items = self.ai.ai_query('string[], 搜索结果列表中包含"auto-wing"相关的标题')
        assert len(items) > 1

        self.ai.ai_assert('检查搜索结果列表第一条标题是否包含"auto-wing"字符串')


if __name__ == '__main__':
    unittest.main()
