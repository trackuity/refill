from __future__ import annotations

import pytest

from refill.filters import Filters, default_filters


def test_copy():
    filters = default_filters.copy()
    filters.register("test", lambda x: x.upper())
    assert filters.apply("testing", "test", []) == "TESTING"
    with pytest.raises(KeyError):
        default_filters.apply("testing", "test", [])


def test_decorator():
    filters = Filters()

    @filters
    def test_filter(x):
        return x.upper()

    assert filters.apply("testing", "test", []) == "TESTING"
