from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Union
from typing_extensions import TypedDict

import pytest

from hydrofile.spec import Selector, Spec, apply_spec, select_data, validate_spec


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


class DummyChartTargetDict(TypedDict):
    categories: List[str]
    series: Dict[str, Dict[str, Union[int, float]]]


class RightDummyTarget(TypedDict):
    variables: Dict[str, str]
    charts: Dict[str, DummyChartTargetDict]


class WrongDummyTarget(TypedDict):
    variables: Dict[str, str]


@pytest.mark.parametrize(
    "data, spec, expected, right_target_cls, wrong_target_cls",
    [
        (
            {
                "item": {"id": "AB12345"},
                "stats": {"views": {"2021-11-01": 1, "2021-11-02": 2, "2021-11-03": 3}},
            },
            {
                "variables": {"item_id": "item.id"},
                "charts": {
                    "views_chart": {
                        "categories": "stats.views|keys",
                        "series": {"views": "stats.views"},
                    }
                },
            },
            {
                "variables": {
                    "item_id": "AB12345",
                },
                "charts": {
                    "views_chart": {
                        "categories": ["2021-11-01", "2021-11-02", "2021-11-03"],
                        "series": {
                            "views": {"2021-11-01": 1, "2021-11-02": 2, "2021-11-03": 3}
                        },
                    }
                },
            },
            RightDummyTarget,
            WrongDummyTarget,
        )
    ],
)
def test_apply_spec(data, spec, expected, right_target_cls, wrong_target_cls):
    assert apply_spec(data, spec) == expected
    validate_spec(right_target_cls, spec)
    with pytest.raises(ValueError) as excinfo:
        validate_spec(wrong_target_cls, spec)
    assert "{'charts'}" in str(excinfo.value)


def test_spec_class():
    class DummyChartSpecDict(TypedDict):
        categories: Selector
        series: Dict[str, Selector]

    @dataclass
    class DummySpec(Spec):
        charts: Dict[str, DummyChartSpecDict]

    spec = DummySpec(
        variables={"item_name": "item.name"},
        charts={
            "views_chart": {
                "categories": "stats.views|keys",
                "series": {"views": "stats.views"},
            }
        },
    )

    assert DummySpec.from_json(spec.to_json()) == spec

    assert spec.apply(
        {
            "item": {"name": "Yolo"},
            "stats": {"views": {"2021-11-01": 1, "2021-11-02": 2}},
        }
    ) == {
        "variables": {"item_name": "Yolo"},
        "charts": {
            "views_chart": {
                "categories": ["2021-11-01", "2021-11-02"],
                "series": {"views": {"2021-11-01": 1, "2021-11-02": 2}},
            }
        },
    }

    class DummyChartTargetDict(TypedDict):
        categories: List[str]
        series: Dict[str, Dict[str, Union[int, float]]]

    class RightDummyTarget(TypedDict):
        variables: Dict[str, str]
        charts: Dict[str, DummyChartTargetDict]

    # No assert as it simply needs to run without raising exceptions.
    # Also, passing globals() and locals() is needed here because the
    # classes above are local, but is typically not needed in practice.
    spec.validate(RightDummyTarget, globals(), locals())

    class WrongDummyTarget(TypedDict):
        variables: Dict[str, str]

    with pytest.raises(ValueError) as excinfo:
        spec.validate(WrongDummyTarget, globals(), locals())
    assert "{'charts'}" in str(excinfo.value)
