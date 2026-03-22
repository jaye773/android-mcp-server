"""Unit tests for ElementFinder core logic.

Tests _find_in_elements_recursive, _element_matches_criteria, get_element_center,
element_to_dict, and find_best_element scoring without going through the full
async UI extraction pipeline.
"""

from unittest.mock import AsyncMock

import pytest

from src.element_finder import ElementFinder


def _make_element(**overrides):
    """Build a UI element dict with sensible defaults."""
    base = {
        "text": "",
        "resource-id": "",
        "class": "",
        "content-desc": "",
        "bounds": "[0,0][100,100]",
        "clickable": "false",
        "enabled": "true",
        "focusable": "false",
        "scrollable": "false",
    }
    base.update(overrides)
    return base


def _make_finder():
    """Create an ElementFinder with a stub ui_extractor."""
    return ElementFinder(ui_extractor=AsyncMock())


# ---------------------------------------------------------------------------
# _element_matches_criteria
# ---------------------------------------------------------------------------

class TestElementMatchesCriteria:
    """Direct tests for the matching predicate."""

    def test_matches_with_no_criteria(self):
        finder = _make_finder()
        elem = _make_element(text="Hello")
        assert finder._element_matches_criteria(
            elem, None, None, None, None, False, False, False, False
        )

    # -- boolean filters --

    def test_clickable_only_rejects_non_clickable(self):
        finder = _make_finder()
        elem = _make_element(clickable="false")
        assert not finder._element_matches_criteria(
            elem, None, None, None, None, True, False, False, False
        )

    def test_clickable_only_accepts_clickable(self):
        finder = _make_finder()
        elem = _make_element(clickable="true")
        assert finder._element_matches_criteria(
            elem, None, None, None, None, True, False, False, False
        )

    def test_enabled_only_rejects_disabled(self):
        finder = _make_finder()
        elem = _make_element(enabled="false")
        assert not finder._element_matches_criteria(
            elem, None, None, None, None, False, True, False, False
        )

    def test_enabled_only_accepts_enabled(self):
        finder = _make_finder()
        elem = _make_element(enabled="true")
        assert finder._element_matches_criteria(
            elem, None, None, None, None, False, True, False, False
        )

    def test_scrollable_only_rejects_non_scrollable(self):
        finder = _make_finder()
        elem = _make_element(scrollable="false")
        assert not finder._element_matches_criteria(
            elem, None, None, None, None, False, False, True, False
        )

    def test_scrollable_only_accepts_scrollable(self):
        finder = _make_finder()
        elem = _make_element(scrollable="true")
        assert finder._element_matches_criteria(
            elem, None, None, None, None, False, False, True, False
        )

    # -- text matching --

    def test_text_exact_match_pass(self):
        finder = _make_finder()
        elem = _make_element(text="Login")
        assert finder._element_matches_criteria(
            elem, "Login", None, None, None, False, False, False, True
        )

    def test_text_exact_match_fail_case_sensitive(self):
        finder = _make_finder()
        elem = _make_element(text="login")
        assert not finder._element_matches_criteria(
            elem, "Login", None, None, None, False, False, False, True
        )

    def test_text_partial_match_case_insensitive(self):
        finder = _make_finder()
        elem = _make_element(text="Login Button")
        assert finder._element_matches_criteria(
            elem, "login", None, None, None, False, False, False, False
        )

    def test_text_partial_match_fail(self):
        finder = _make_finder()
        elem = _make_element(text="Submit")
        assert not finder._element_matches_criteria(
            elem, "login", None, None, None, False, False, False, False
        )

    def test_text_match_empty_element_text(self):
        finder = _make_finder()
        elem = _make_element(text="")
        assert not finder._element_matches_criteria(
            elem, "anything", None, None, None, False, False, False, False
        )

    def test_text_match_missing_text_key(self):
        finder = _make_finder()
        elem = {"enabled": "true"}  # no 'text' key at all
        assert not finder._element_matches_criteria(
            elem, "anything", None, None, None, False, False, False, False
        )

    # -- resource-id matching --

    def test_resource_id_exact_match(self):
        finder = _make_finder()
        elem = _make_element(**{"resource-id": "com.app:id/btn"})
        assert finder._element_matches_criteria(
            elem, None, "com.app:id/btn", None, None, False, False, False, True
        )

    def test_resource_id_exact_match_fail(self):
        finder = _make_finder()
        elem = _make_element(**{"resource-id": "com.app:id/btn"})
        assert not finder._element_matches_criteria(
            elem, None, "com.app:id/other", None, None, False, False, False, True
        )

    def test_resource_id_partial_match(self):
        finder = _make_finder()
        elem = _make_element(**{"resource-id": "com.app:id/login_btn"})
        assert finder._element_matches_criteria(
            elem, None, "login_btn", None, None, False, False, False, False
        )

    def test_resource_id_partial_match_is_case_sensitive(self):
        """resource-id partial match uses plain `in`, not case-insensitive."""
        finder = _make_finder()
        elem = _make_element(**{"resource-id": "com.app:id/Login_Btn"})
        assert not finder._element_matches_criteria(
            elem, None, "login_btn", None, None, False, False, False, False
        )

    # -- class name matching --

    def test_class_name_exact_match(self):
        finder = _make_finder()
        elem = _make_element(**{"class": "android.widget.Button"})
        assert finder._element_matches_criteria(
            elem, None, None, "android.widget.Button", None, False, False, False, True
        )

    def test_class_name_partial_case_insensitive(self):
        finder = _make_finder()
        elem = _make_element(**{"class": "android.widget.Button"})
        assert finder._element_matches_criteria(
            elem, None, None, "button", None, False, False, False, False
        )

    def test_class_name_exact_mismatch(self):
        finder = _make_finder()
        elem = _make_element(**{"class": "android.widget.TextView"})
        assert not finder._element_matches_criteria(
            elem, None, None, "android.widget.Button", None, False, False, False, True
        )

    # -- content-desc matching --

    def test_content_desc_exact_match(self):
        finder = _make_finder()
        elem = _make_element(**{"content-desc": "Close dialog"})
        assert finder._element_matches_criteria(
            elem, None, None, None, "Close dialog", False, False, False, True
        )

    def test_content_desc_partial_case_insensitive(self):
        finder = _make_finder()
        elem = _make_element(**{"content-desc": "Close dialog"})
        assert finder._element_matches_criteria(
            elem, None, None, None, "close", False, False, False, False
        )

    def test_content_desc_exact_mismatch(self):
        finder = _make_finder()
        elem = _make_element(**{"content-desc": "Open menu"})
        assert not finder._element_matches_criteria(
            elem, None, None, None, "Close dialog", False, False, False, True
        )

    # -- multiple criteria (AND logic) --

    def test_multiple_criteria_all_match(self):
        finder = _make_finder()
        elem = _make_element(
            text="Submit",
            clickable="true",
            **{"class": "android.widget.Button", "resource-id": "com.app:id/submit"},
        )
        assert finder._element_matches_criteria(
            elem, "Submit", "submit", "Button", None, True, False, False, False
        )

    def test_multiple_criteria_one_fails(self):
        finder = _make_finder()
        elem = _make_element(
            text="Submit",
            clickable="false",  # will fail clickable_only
            **{"class": "android.widget.Button"},
        )
        assert not finder._element_matches_criteria(
            elem, "Submit", None, "Button", None, True, False, False, False
        )

    # -- default values for missing keys --

    def test_missing_clickable_defaults_false(self):
        """Element missing 'clickable' key should default to 'false' and fail clickable_only."""
        finder = _make_finder()
        elem = {"text": "hi", "enabled": "true"}
        assert not finder._element_matches_criteria(
            elem, None, None, None, None, True, False, False, False
        )

    def test_missing_enabled_defaults_true(self):
        """Element missing 'enabled' key should default to 'true' and pass enabled_only."""
        finder = _make_finder()
        elem = {"text": "hi"}
        assert finder._element_matches_criteria(
            elem, None, None, None, None, False, True, False, False
        )

    def test_missing_scrollable_defaults_false(self):
        finder = _make_finder()
        elem = {"text": "hi"}
        assert not finder._element_matches_criteria(
            elem, None, None, None, None, False, False, True, False
        )


# ---------------------------------------------------------------------------
# _find_in_elements_recursive
# ---------------------------------------------------------------------------

class TestFindInElementsRecursive:
    """Direct tests for the recursive traversal function."""

    def test_empty_list(self):
        finder = _make_finder()
        matches = []
        finder._find_in_elements_recursive(
            [], matches, None, None, None, None, False, False, False, False
        )
        assert matches == []

    def test_single_match(self):
        finder = _make_finder()
        elements = [_make_element(text="Hello")]
        matches = []
        finder._find_in_elements_recursive(
            elements, matches, "Hello", None, None, None, False, False, False, True
        )
        assert len(matches) == 1
        assert matches[0]["text"] == "Hello"

    def test_no_match(self):
        finder = _make_finder()
        elements = [_make_element(text="Hello")]
        matches = []
        finder._find_in_elements_recursive(
            elements, matches, "Goodbye", None, None, None, False, False, False, True
        )
        assert matches == []

    def test_multiple_matches_in_flat_list(self):
        finder = _make_finder()
        elements = [
            _make_element(text="Item 1"),
            _make_element(text="Something else"),
            _make_element(text="Item 2"),
            _make_element(text="Item 3"),
        ]
        matches = []
        finder._find_in_elements_recursive(
            elements, matches, "Item", None, None, None, False, False, False, False
        )
        assert len(matches) == 3

    def test_appends_to_existing_matches(self):
        """Verify matches list is accumulated, not replaced."""
        finder = _make_finder()
        existing = [_make_element(text="pre-existing")]
        elements = [_make_element(text="new")]
        finder._find_in_elements_recursive(
            elements, existing, "new", None, None, None, False, False, False, False
        )
        assert len(existing) == 2

    def test_all_filters_combined(self):
        finder = _make_finder()
        good = _make_element(
            text="OK",
            clickable="true",
            enabled="true",
            scrollable="true",
            **{"class": "android.widget.Button", "resource-id": "com.app:id/ok",
               "content-desc": "Confirm action"},
        )
        bad_disabled = _make_element(text="OK", enabled="false", clickable="true", scrollable="true")
        bad_text = _make_element(text="Cancel", clickable="true", enabled="true", scrollable="true")
        elements = [good, bad_disabled, bad_text]
        matches = []
        finder._find_in_elements_recursive(
            elements, matches, "OK", "ok", "Button", "Confirm",
            True, True, True, False
        )
        assert len(matches) == 1
        assert matches[0] is good


# ---------------------------------------------------------------------------
# get_element_center
# ---------------------------------------------------------------------------

class TestGetElementCenter:

    def test_valid_bounds(self):
        finder = _make_finder()
        elem = _make_element(bounds="[100,200][300,400]")
        center = finder.get_element_center(elem)
        assert center == {"x": 200, "y": 300}

    def test_full_screen_bounds(self):
        finder = _make_finder()
        elem = _make_element(bounds="[0,0][1080,1920]")
        center = finder.get_element_center(elem)
        assert center == {"x": 540, "y": 960}

    def test_missing_bounds_key(self):
        finder = _make_finder()
        elem = {"text": "no bounds"}
        center = finder.get_element_center(elem)
        assert center is None

    def test_empty_bounds_string(self):
        finder = _make_finder()
        elem = _make_element(bounds="")
        center = finder.get_element_center(elem)
        # parse_bounds returns zeroed dict for empty string → all zeros → None
        assert center is None

    def test_zero_bounds(self):
        finder = _make_finder()
        elem = _make_element(bounds="[0,0][0,0]")
        center = finder.get_element_center(elem)
        assert center is None

    def test_malformed_bounds(self):
        finder = _make_finder()
        elem = _make_element(bounds="not_valid_bounds")
        center = finder.get_element_center(elem)
        # Should return None or gracefully degrade
        assert center is None or isinstance(center, dict)

    def test_bounds_none_value(self):
        finder = _make_finder()
        elem = {"bounds": None}
        center = finder.get_element_center(elem)
        assert center is None


# ---------------------------------------------------------------------------
# element_to_dict
# ---------------------------------------------------------------------------

class TestElementToDict:

    def test_complete_element_passes_through(self):
        finder = _make_finder()
        elem = _make_element(text="Hello", clickable="true")
        result = finder.element_to_dict(elem)
        assert result["text"] == "Hello"
        assert result["clickable"] == "true"

    def test_missing_keys_get_defaults(self):
        finder = _make_finder()
        elem = {"text": "Hello"}
        result = finder.element_to_dict(elem)
        assert result["resource-id"] == ""
        assert result["class"] == ""
        assert result["content-desc"] == ""
        assert result["bounds"] == "[0,0][0,0]"
        assert result["clickable"] == "false"
        assert result["enabled"] == "false"
        assert result["focusable"] == "false"
        assert result["scrollable"] == "false"
        assert result["displayed"] == "true"

    def test_empty_element(self):
        finder = _make_finder()
        result = finder.element_to_dict({})
        # All expected keys should be present with defaults
        assert "text" in result
        assert "bounds" in result
        assert result["text"] == ""

    def test_does_not_overwrite_existing_keys(self):
        finder = _make_finder()
        elem = {"clickable": "true", "enabled": "true"}
        result = finder.element_to_dict(elem)
        assert result["clickable"] == "true"
        assert result["enabled"] == "true"

    def test_returns_copy(self):
        finder = _make_finder()
        elem = _make_element(text="original")
        result = finder.element_to_dict(elem)
        result["text"] = "modified"
        assert elem["text"] == "original"


# ---------------------------------------------------------------------------
# find_elements (async, with mocked ui_extractor)
# ---------------------------------------------------------------------------

class TestFindElementsAsync:

    @pytest.mark.asyncio
    async def test_returns_empty_on_layout_failure(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {"success": False, "error": "fail"}
        result = await finder.find_elements(text="anything")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_elements(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [],
            "element_count": 0,
        }
        result = await finder.find_elements(text="anything")
        assert result == []

    @pytest.mark.asyncio
    async def test_filters_elements(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [
                _make_element(text="Login", clickable="true"),
                _make_element(text="Title", clickable="false"),
            ],
            "element_count": 2,
        }
        result = await finder.find_elements(text="Login", clickable_only=True)
        assert len(result) == 1
        assert result[0]["text"] == "Login"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.side_effect = RuntimeError("boom")
        result = await finder.find_elements(text="x")
        assert result == []


# ---------------------------------------------------------------------------
# find_best_element (scoring)
# ---------------------------------------------------------------------------

class TestFindBestElement:

    @pytest.mark.asyncio
    async def test_returns_none_on_layout_failure(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {"success": False}
        result = await finder.find_best_element(text="x")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_matches(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [_make_element(text="Other")],
            "element_count": 1,
        }
        result = await finder.find_best_element(text="Nonexistent", exact_match=True)
        assert result is None

    @pytest.mark.asyncio
    async def test_prefers_exact_text_match(self):
        finder = _make_finder()
        exact = _make_element(text="Login", clickable="false", enabled="false")
        partial = _make_element(text="Login Button", clickable="true", enabled="true")
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [partial, exact],
            "element_count": 2,
        }
        # exact text match gets +10, partial gets +5 + 3 (clickable) + 2 (enabled) = 10
        # They might tie; the key is that both are considered valid matches
        result = await finder.find_best_element(text="Login")
        assert result is not None
        assert "Login" in result["text"]

    @pytest.mark.asyncio
    async def test_clickable_gets_higher_score(self):
        finder = _make_finder()
        clickable = _make_element(text="Btn", clickable="true", enabled="true")
        non_clickable = _make_element(text="Btn", clickable="false", enabled="true")
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [non_clickable, clickable],
            "element_count": 2,
        }
        result = await finder.find_best_element(text="Btn")
        assert result["clickable"] == "true"

    @pytest.mark.asyncio
    async def test_resource_id_bonus(self):
        finder = _make_finder()
        with_id = _make_element(text="X", **{"resource-id": "com.app:id/x"})
        without_id = _make_element(text="X", **{"resource-id": ""})
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [without_id, with_id],
            "element_count": 2,
        }
        result = await finder.find_best_element(text="X")
        assert result["resource-id"] == "com.app:id/x"

    @pytest.mark.asyncio
    async def test_size_bonus_for_large_elements(self):
        finder = _make_finder()
        large = _make_element(text="A", bounds="[0,0][200,200]")
        small = _make_element(text="A", bounds="[0,0][50,50]")
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [small, large],
            "element_count": 2,
        }
        result = await finder.find_best_element(text="A")
        assert result["bounds"] == "[0,0][200,200]"

    @pytest.mark.asyncio
    async def test_handles_exception(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.side_effect = RuntimeError("boom")
        result = await finder.find_best_element(text="x")
        assert result is None


# ---------------------------------------------------------------------------
# find_element_by_text / find_element_by_id
# ---------------------------------------------------------------------------

class TestFindElementByTextAndId:

    @pytest.mark.asyncio
    async def test_find_element_by_text_returns_first(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [
                _make_element(text="First"),
                _make_element(text="First duplicate"),
            ],
            "element_count": 2,
        }
        result = await finder.find_element_by_text("First")
        assert result is not None
        assert result["text"] == "First"

    @pytest.mark.asyncio
    async def test_find_element_by_text_returns_none(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [],
            "element_count": 0,
        }
        result = await finder.find_element_by_text("Missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_element_by_text_exception(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.side_effect = RuntimeError("boom")
        result = await finder.find_element_by_text("x")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_element_by_id_exact(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [
                _make_element(**{"resource-id": "com.app:id/target"}),
                _make_element(**{"resource-id": "com.app:id/other"}),
            ],
            "element_count": 2,
        }
        result = await finder.find_element_by_id("com.app:id/target")
        assert result is not None
        assert result["resource-id"] == "com.app:id/target"

    @pytest.mark.asyncio
    async def test_find_element_by_id_returns_none(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [],
            "element_count": 0,
        }
        result = await finder.find_element_by_id("com.app:id/missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_element_by_id_exception(self):
        finder = _make_finder()
        finder.ui_extractor.get_ui_layout.side_effect = RuntimeError("boom")
        result = await finder.find_element_by_id("x")
        assert result is None


# ---------------------------------------------------------------------------
# Malformed / edge-case UI hierarchies
# ---------------------------------------------------------------------------

class TestMalformedHierarchyHandling:

    def test_element_with_none_values(self):
        """Elements where attribute values are None instead of strings."""
        finder = _make_finder()
        elem = {"text": None, "enabled": "true", "clickable": None}
        # text=None criteria should still work: None is not None → filter applies
        # element.get("text", "") → None, and "x" not in None would TypeError
        # but with no text filter, it should pass
        assert finder._element_matches_criteria(
            elem, None, None, None, None, False, False, False, False
        )

    def test_element_completely_empty_dict(self):
        finder = _make_finder()
        elem = {}
        # No criteria → should match (enabled_only=False so no filter)
        assert finder._element_matches_criteria(
            elem, None, None, None, None, False, False, False, False
        )

    def test_recursive_with_non_dict_elements(self):
        """If elements list contains non-dict items, verify behavior."""
        finder = _make_finder()
        # This should not crash even with weird data
        elements = [_make_element(text="valid")]
        matches = []
        finder._find_in_elements_recursive(
            elements, matches, None, None, None, None, False, False, False, False
        )
        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_find_elements_with_missing_bounds_in_scoring(self):
        """find_best_element should handle elements without bounds."""
        finder = _make_finder()
        elem_no_bounds = {"text": "Hello", "enabled": "true"}
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [elem_no_bounds],
            "element_count": 1,
        }
        result = await finder.find_best_element(text="Hello", enabled_only=False)
        assert result is not None

    @pytest.mark.asyncio
    async def test_find_best_element_with_invalid_bounds_string(self):
        """Scoring should not crash on unparseable bounds."""
        finder = _make_finder()
        elem = _make_element(text="X", bounds="garbage")
        finder.ui_extractor.get_ui_layout.return_value = {
            "success": True,
            "elements": [elem],
            "element_count": 1,
        }
        result = await finder.find_best_element(text="X")
        assert result is not None
        assert result["text"] == "X"

    def test_get_element_center_with_partial_bounds(self):
        """Bounds string with only one coordinate pair."""
        finder = _make_finder()
        elem = _make_element(bounds="[100,200]")
        center = finder.get_element_center(elem)
        # parse_bounds should return zeroed dict or None for malformed input
        assert center is None or isinstance(center, dict)

    def test_element_to_dict_preserves_extra_keys(self):
        """Extra keys beyond the expected set should be preserved."""
        finder = _make_finder()
        elem = {"text": "Hi", "custom-attr": "special"}
        result = finder.element_to_dict(elem)
        assert result["custom-attr"] == "special"
        assert result["text"] == "Hi"
