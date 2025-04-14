import re


def selector_to_locator(selector: str) -> str:
    """
    selector to playwright locator
    :param selector:
    :return:
    """
    if '[text()=' in selector:
        return re.sub(
            r'\[text\(\)\s*=\s*(?P<quote>[\'"])(?P<content>.*?)(?P=quote)\]',
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
    if '[text()=' in selector:
        pattern = re.compile(r'\[text\(\)\s*=\s*(?P<quote>[\'"])(?P<content>.*?)(?P=quote)\]')
        return pattern.sub(r'[contains(text(),\g<quote>\g<content>\g<quote>)]', selector)

    return selector
