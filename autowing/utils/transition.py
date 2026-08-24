import re

_TEXT_PREDICATE_PATTERN = re.compile(
    r'\[text\(\)\s*=\s*(?P<quote>[\'"])(?P<content>.*?)(?P=quote)\]')


def selector_to_locator(selector: str) -> str:
    """
    selector to playwright locator
    :param selector:
    :return:
    """
    if _TEXT_PREDICATE_PATTERN.search(selector):
        return _TEXT_PREDICATE_PATTERN.sub(
            lambda m: f':has-text({m.group("quote")}{m.group("content")}{m.group("quote")})',
            selector
        )

    return selector


def selector_to_selenium(selector: str) -> str:
    """
    selector to selenium
    :param selector:
    :return:
    """
    if _TEXT_PREDICATE_PATTERN.search(selector):
        return _TEXT_PREDICATE_PATTERN.sub(
            r'[contains(text(),\g<quote>\g<content>\g<quote>)]', selector)

    return selector
