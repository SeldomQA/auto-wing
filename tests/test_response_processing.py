"""Unit tests for the shared LLM response processing logic (plan item T1).

Covers the pure-logic helpers of AiFixtureBase that previously had zero
test protection: response cleaning, result format validation, format-hint
parsing, text fallback extraction, boolean parsing, empty-key pruning and
the context summary builder. No browser or LLM needed.
"""
import pytest

from autowing.core.ai_fixture_base import AiFixtureBase


@pytest.fixture()
def base():
    """Bare instance - only the static/pure helpers are exercised."""
    return AiFixtureBase.__new__(AiFixtureBase)


class TestCleanResponse:
    def test_plain_json_untouched(self, base):
        assert base._clean_response('{"selector": "#a"}') == '{"selector": "#a"}'

    @pytest.mark.parametrize("response", ["", None, 123, []])
    def test_empty_and_non_string(self, base, response):
        assert base._clean_response(response) == ""

    def test_json_code_block_extracted(self, base):
        raw = 'Here you go:\n```json\n{"selector": "#a"}\n```\nDone.'
        assert base._clean_response(raw) == '{"selector": "#a"}'

    def test_plain_code_block_extracted(self, base):
        assert base._clean_response('```\ntrue\n```') == "true"

    def test_leading_language_line_stripped(self, base):
        raw = '```json\njson\n{"ok": 1}\n```'
        assert base._clean_response(raw) == '{"ok": 1}'

    def test_surrounding_whitespace_stripped(self, base):
        assert base._clean_response('  \n "yes" \n ') == '"yes"'

    def test_unbalanced_code_fences_keep_content(self, base):
        # A ```json prefix is still extracted even without proper newlines
        assert base._clean_response('```json {"a": 1} ```') == '{"a": 1}'


class TestValidateResultFormat:
    def test_no_hint_returns_result_as_is(self, base):
        assert base._validate_result_format({"k": 1}, "") == {"k": 1}

    def test_string_array_passes_through(self, base):
        assert base._validate_result_format(["a", "b"], "string[]") == ["a", "b"]

    def test_string_array_wraps_scalar(self, base):
        assert base._validate_result_format("solo", "string[]") == ["solo"]

    def test_string_array_coerces_items(self, base):
        assert base._validate_result_format([1, 2.5], "string[]") == ["1", "2.5"]

    def test_number_array_passes_through(self, base):
        assert base._validate_result_format([1, 2], "number[]") == [1.0, 2.0]

    def test_number_array_wraps_scalar(self, base):
        assert base._validate_result_format("3", "number[]") == [3.0]

    def test_number_array_rejects_non_numeric(self, base):
        with pytest.raises(ValueError, match="Cannot convert"):
            base._validate_result_format(["abc"], "number[]")

    def test_unknown_hint_returns_result_as_is(self, base):
        assert base._validate_result_format("x", "object[]") == "x"


class TestParseFormatHint:
    @pytest.mark.parametrize("hint", ["string[]", "number[]", "object[]"])
    def test_leading_hint_extracted(self, base, hint):
        got_hint, rest = base._parse_format_hint(f"{hint}, list all prices")
        assert got_hint == hint
        assert rest == "list all prices"

    def test_no_hint(self, base):
        assert base._parse_format_hint("what is the title") == ("", "what is the title")

    def test_hint_without_query(self, base):
        assert base._parse_format_hint("string[]") == ("string[]", "")


class TestExtractQueryFromText:
    def test_matching_lines_extracted_and_deduplicated(self, base):
        # Bullet/heading lines are filtered out; duplicate hits are dropped
        text = "the login page title\nthe login page title\n- skipped bullet\nirrelevant line"
        result = base._extract_query_from_text(text, "what is the login page title", "string[]")
        assert result == ["the login page title"]

    def test_key_value_prefix_stripped(self, base):
        text = "Answer: the dashboard summary"
        result = base._extract_query_from_text(text, "what is the dashboard summary", "string[]")
        assert result == ["the dashboard summary"]

    def test_non_string_array_hint_returns_none(self, base):
        assert base._extract_query_from_text("whatever", "query", "number[]") is None

    def test_no_matching_terms_returns_none(self, base):
        assert base._extract_query_from_text("nothing here", "unrelated long query", "string[]") is None


class TestParseBooleanResponse:
    def test_exact_values(self, base):
        assert AiFixtureBase._parse_boolean_response("true") is True
        assert AiFixtureBase._parse_boolean_response("false") is False

    def test_boolean_word_embedded_in_text(self, base):
        assert AiFixtureBase._parse_boolean_response("the answer is true") is True
        assert AiFixtureBase._parse_boolean_response("no, false") is False

    def test_unparseable_raises(self, base):
        with pytest.raises(ValueError, match="Failed to parse assertion"):
            AiFixtureBase._parse_boolean_response("maybe so")


class TestRemoveEmptyKeys:
    def test_empty_list(self, base):
        assert base._remove_empty_keys([]) == []

    def test_none_entries_skipped(self, base):
        assert base._remove_empty_keys([None, {"a": 1}]) == [{"a": 1}]

    def test_empty_and_none_values_pruned(self, base):
        result = base._remove_empty_keys(
            [{"text": "登录", "id": "", "cls": None, "zero": 0}])
        assert result == [{"text": "登录", "zero": 0}]


class TestContextSummary:
    def test_web_context(self):
        lines = AiFixtureBase._get_context_summary(
            {"url": "https://a.com", "title": "Home"})
        assert lines == "Page: https://a.com\nTitle: Home"

    def test_app_context(self):
        lines = AiFixtureBase._get_context_summary(
            {"activity": ".Main", "package": "com.app"})
        assert lines == "Activity: .Main\nPackage: com.app"

    def test_empty_context(self):
        assert AiFixtureBase._get_context_summary({}) == ""
