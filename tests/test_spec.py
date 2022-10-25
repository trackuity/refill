from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Dict, List, Union

import pytest
from typing_extensions import TypedDict

from refill.filters import default_filters
from refill.spec import Selector, Spec, apply_spec, select_data, validate_spec


@pytest.mark.parametrize(
    "selector, expected",
    [
        ("numbers", [1, 2, 4]),
        ("languages.iso", ["EN", "NL", "FR"]),
        ("stats.views|keys", ["2021-11-02", "2021-11-01", "2021-11-03"]),
        ("stats.views|keys|sort", ["2021-11-01", "2021-11-02", "2021-11-03"]),
        ("stats.views|sort|keys", ["2021-11-01", "2021-11-02", "2021-11-03"]),
        ("stats.views|keys|keys", [0, 1, 2]),
        ("stats.views|values", [12, 10, 14]),
        ("numbers|values", [1, 2, 4]),
        ("numbers|reverse", [4, 2, 1]),
        ("person.name|lower", "john doe"),
        ("person.name|upper", "JOHN DOE"),
        ("languages.iso|lower", ["en", "nl", "fr"]),
        ("languages.iso|upper", ["EN", "NL", "FR"]),
        ("languages|first|lower", {"iso": "en"}),
        ("languages|first|upper", {"iso": "EN"}),
        ("person.age|str", "45"),
        ("person.age|str()", "45"),
        ("person.age|str|int", 45),
        ("person.age|selfie", {45: 45}),
        ("person.age|str|selfie", {"45": "45"}),
        ("numbers|head(2)|selfie", {1: 1, 2: 2}),
        ("numbers|first", 1),
        ("numbers|last", 4),
        ("numbers|head", [1]),
        ("numbers|head(2)", [1, 2]),
        ("numbers|tail", [4]),
        ("numbers|tail(2)", [2, 4]),
        ("numbers|tail(2)|head(1)", [2]),
        ("numbers|sum", sum([1, 2, 4])),
        ("numbers|cumul", [1, 3, 7]),
        ("stats.views|values|sum", sum([12, 10, 14])),
        ("stats.views|cumul|tail", {"2021-11-03": 36}),
        ("stats.views|head", {"2021-11-02": 12}),
        ("stats.views|tail", {"2021-11-03": 14}),
        ("stats.views|reverse|head", {"2021-11-03": 14}),
        ("person.weight_in_grams|format_number", "75,148"),
        ("person.weight_in_grams|format_currency", "$75,148.00"),
        ("person.weight_in_grams|format_currency(EUR)", "€75,148.00"),
        ("person.weight_in_grams|format_currency('EUR')", "€75,148.00"),
        ("conversion_rate|format_percent", "25%"),
        ("conversion_rate|format_percent('# %')", "25 %"),
        ("stats.views|keys|first|format_date('MMM d, ''''yy')", "Nov 2, '21"),
        ("stats.views|keys|head(1)|format_date", ["Nov 2, 2021"]),
        ("creation_year|selfie|format_date('MMM yyyy')", {"2021": "Jan 2021"}),
        ("stats.views|head(1)|format_number", {"2021-11-02": "12"}),
        ("stats.views|head(1)|format_currency", {"2021-11-02": "$12.00"}),
        ("person.data_urls|first|fetch", b'"testdata"'),
        ("person.data_urls|fetch", [b'"testdata"']),
        ("person.data_urls|first|fetch|str(UTF8)", '"testdata"'),
        ("person.data_urls|first|fetch|str('utf-8')", '"testdata"'),
        ("person.name,person.age,person.age", ["John Doe", 45, 45]),
        ("numbers,numbers", [[1, 2, 4], [1, 2, 4]]),
        ("(stats.views,stats.conversions)|sum|head", {"2021-11-02": 15}),
        ("(stats.views,stats.conversions)|sum|head(2)|tail", {"2021-11-01": 10}),
        ("numbers+numbers", [1, 2, 4, 1, 2, 4]),
        ("(numbers+numbers)", [1, 2, 4, 1, 2, 4]),
        ("numbers|first + numbers|last", 5),
        ("(numbers|first) + (numbers|last)", 5),
        ("numbers|first / numbers|last", 0.25),
        ("(numbers|first + numbers|last) / numbers|last", 1.25),
        ("numbers|first + numbers|last * numbers|last", 17),
        ("stats.views|values|head(1)|last + stats.views|values|head(2)|last", 22),
    ],
)
def test_select_data(selector, expected):
    data = {
        "numbers": [1, 2, 4],
        "languages": [{"iso": "EN"}, {"iso": "NL"}, {"iso": "FR"}],
        "conversion_rate": 0.253,
        "creation_year": "2021",
        "stats": {
            "views": {"2021-11-02": 12, "2021-11-01": 10, "2021-11-03": 14},
            "conversions": {"2021-11-02": 3},
        },
        "person": {
            "name": "John Doe",
            "age": 45,
            "weight_in_grams": 75148,
            "data_urls": [
                "data:{};base64,{}".format(
                    "application/json",
                    base64.b64encode(json.dumps("testdata").encode()).decode(),
                )
            ],
        },
    }
    assert select_data(data, selector) == expected


def test_select_data_with_custom_filters():
    filters = default_filters.copy()
    filters.register("test", lambda x: "test" + x)
    assert select_data({"name": "jenny"}, "name|test", filters=filters) == "testjenny"
    assert select_data({"name": "jenny"}, "name|upper", filters=filters) == "JENNY"


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
                "item": {
                    "id": "AB12345",
                    "name": "test item",
                    "weight": 80,
                    "height": 16,
                },
                "stats": {"views": {"2021-11-01": 1, "2021-11-02": 2, "2021-11-03": 3}},
            },
            {
                "variables": {
                    "item_id": "item.id",
                    "iid": "=item_id|lower",
                    "item_name?": "item.name",
                    "ignore_me?": "doesnotexist",
                    "ignore_me_too?": "=doesnotexist",
                    "weight": "item.weight",
                    "height": "item.height",
                    "ratio": "=weight / =height",
                },
                "charts": {
                    "views_chart": {
                        "categories": "stats.views|keys",
                        "series": {"views": "stats.views", "vws": "=views"},
                    }
                },
            },
            {
                "variables": {
                    "item_id": "AB12345",
                    "iid": "ab12345",
                    "item_name": "test item",
                    "weight": 80,
                    "height": 16,
                    "ratio": 80 / 16,
                },
                "charts": {
                    "views_chart": {
                        "categories": ["2021-11-01", "2021-11-02", "2021-11-03"],
                        "series": {
                            "views": {
                                "2021-11-01": 1,
                                "2021-11-02": 2,
                                "2021-11-03": 3,
                            },
                            "vws": {"2021-11-01": 1, "2021-11-02": 2, "2021-11-03": 3},
                        },
                    }
                },
            },
            RightDummyTarget,
            WrongDummyTarget,
        )
    ],
)
def test_spec_functions(data, spec, expected, right_target_cls, wrong_target_cls):
    assert apply_spec(spec, data) == expected
    validate_spec(spec, right_target_cls)
    with pytest.raises(ValueError) as excinfo:
        validate_spec(spec, wrong_target_cls)
    assert "{'charts'}" in str(excinfo.value)


def test_spec_class():
    class DummyChartSpecDict(TypedDict):
        categories: Selector
        series: Dict[str, Selector]

    @dataclass
    class DummySpec(Spec):
        variables: Dict[str, Selector]
        charts: Dict[str, DummyChartSpecDict]

    spec = DummySpec(
        variables={
            "item_name": "item.name",
            "item_price": "item.price|format_currency(EUR)",
        },
        charts={
            "views_chart": {
                "categories": "stats.views|keys",
                "series": {"views": "stats.views"},
            }
        },
    )

    assert Spec.from_json(spec.to_json()) == spec

    # check if it works for non-dataclass spec too
    plain_spec = Spec.from_dict(spec.to_dict())
    assert Spec.from_json(plain_spec.to_json()) == plain_spec

    data_dict = {
        "item": {"name": "Yolo", "price": 84.95},
        "stats": {"views": {"2021-11-01": 1, "2021-11-02": 2}},
    }
    expected_dict = {
        "variables": {"item_name": "Yolo", "item_price": "€\xa084,95"},
        "charts": {
            "views_chart": {
                "categories": ["2021-11-01", "2021-11-02"],
                "series": {"views": {"2021-11-01": 1, "2021-11-02": 2}},
            }
        },
    }

    assert spec.apply(data_dict, locale="nl_BE") == expected_dict

    class RightLocalTarget(TypedDict):
        variables: Dict[str, str]
        charts: Dict[str, DummyChartTargetDict]

    # No assert as it simply needs to run without raising exceptions.
    # Also, passing globals() and locals() is needed here because the
    # classes above are local, but is typically not needed in practice.
    spec.validate(RightLocalTarget, globals(), locals())

    class WrongLocalTarget(TypedDict):
        variables: Dict[str, str]

    with pytest.raises(ValueError) as excinfo:
        spec.validate(WrongLocalTarget, globals(), locals())
    assert "{'charts'}" in str(excinfo.value)
