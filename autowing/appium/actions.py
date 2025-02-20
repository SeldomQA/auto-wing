from time import sleep as sys_sleep

from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput


class Action:
    """
    Encapsulate basic actions: tap, etc
    """

    def __init__(self, driver=None):
        self.driver = driver

    def tap(self, x: int, y: int, pause: float = 0.1, sleep: float = 1) -> None:
        """
        Tap on the coordinates
        :param x: x coordinates
        :param y: y coordinates
        :param pause: pause time
        :param sleep: sleep time
        :return:
        """
        logger.info(f"👆 top x={x},y={y}.")
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to_location(x, y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pause(pause)
        actions.w3c_actions.pointer_action.release()
        actions.perform()
        sys_sleep(sleep)
