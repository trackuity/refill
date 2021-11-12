from __future__ import annotations

import pytest

from hydrofile.spec import apply_spec, select_data


@pytest.mark.parametrize(
    "selector, expected",
    [
        ("numbers", [1, 2, 4]),
        ("languages.iso", ["EN", "NL", "FR"]),
        ("stats.views|keys", ["2021-11-01", "2021-11-02", "2021-11-03"]),
        ("stats.views|keys|keys", [0, 1, 2]),
    ],
)
def test_select_data(selector, expected):
    data = {
        "numbers": [1, 2, 4],
        "languages": [{"iso": "EN"}, {"iso": "NL"}, {"iso": "FR"}],
        "stats": {
            "views": {"2021-11-02": 12, "2021-11-01": 10, "2021-11-03": 14},
        },
    }
    assert select_data(data, selector) == expected


@pytest.mark.parametrize(
    "data, spec, expected",
    [
        (
            {"stats": {"views": {"2021-11-01": 1, "2021-11-02": 2, "2021-11-03": 3}}},
            {
                "charts": {
                    "mychart": {
                        "categories": "stats.views|keys",
                        "series": {"views": "stats.views"},
                    }
                }
            },
            {
                "charts": {
                    "mychart": {
                        "categories": ["2021-11-01", "2021-11-02", "2021-11-03"],
                        "series": {
                            "views": {"2021-11-01": 1, "2021-11-02": 2, "2021-11-03": 3}
                        },
                    }
                }
            },
        )
    ],
)
def test_apply_spec(data, spec, expected):
    assert apply_spec(data, spec) == expected
