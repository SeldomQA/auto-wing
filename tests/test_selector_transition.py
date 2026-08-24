"""Unit tests for selector transition helpers (plan item T1).

selector_to_locator / selector_to_selenium rewrite XPath [text()=...]
predicates into the form each driver understands.
"""
from autowing.utils.transition import selector_to_locator, selector_to_selenium


class TestSelectorToLocator:
    def test_css_selector_passthrough(self):
        assert selector_to_locator("input#sb_form_q") == "input#sb_form_q"

    def test_plain_xpath_passthrough(self):
        assert selector_to_locator("//button[@id='submit']") == "//button[@id='submit']"

    def test_text_predicate_double_quotes(self):
        assert selector_to_locator('//button[text()="登录"]') == '//button:has-text("登录")'

    def test_text_predicate_single_quotes(self):
        assert selector_to_locator("//a[text()='next page']") == "//a:has-text('next page')"

    def test_text_predicate_with_whitespace(self):
        assert selector_to_locator("//a[text() = 'next']") == "//a:has-text('next')"


class TestSelectorToSelenium:
    def test_plain_xpath_passthrough(self):
        assert selector_to_selenium("//button[@id='submit']") == "//button[@id='submit']"

    def test_text_predicate_double_quotes(self):
        assert selector_to_selenium('//button[text()="登录"]') == \
            '//button[contains(text(),"登录")]'

    def test_text_predicate_single_quotes(self):
        assert selector_to_selenium("//a[text()='next page']") == \
            "//a[contains(text(),'next page')]"
