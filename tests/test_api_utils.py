"""Tests for API utility functions."""

from __future__ import annotations

import pytest

from pykalshi.api._utils import strip_none, validate_path_param


class TestStripNone:
    def test_removes_none_values(self) -> None:
        assert strip_none({"a": 1, "b": None, "c": "x"}) == {"a": 1, "c": "x"}

    def test_empty_dict(self) -> None:
        assert strip_none({}) == {}

    def test_all_none(self) -> None:
        assert strip_none({"a": None, "b": None}) == {}

    def test_preserves_falsy_non_none(self) -> None:
        assert strip_none({"a": 0, "b": "", "c": False}) == {"a": 0, "b": "", "c": False}


class TestValidatePathParam:
    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="order_id"):
            validate_path_param("order_id", "")

    def test_valid_string_passes(self) -> None:
        validate_path_param("order_id", "abc-123")
