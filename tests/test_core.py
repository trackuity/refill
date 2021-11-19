from __future__ import annotations

from dataclasses import dataclass
from typing import IO, Dict, List, Union

import pytest
from refill.core import Filler, Params, Template
from refill.spec import Selector, Spec, format_currency_filter
from typing_extensions import TypedDict


class DummyChartSpecDict(TypedDict):
    categories: Selector
    series: Dict[str, Selector]


@dataclass
class DummySpec(Spec):
    variables: Dict[str, Selector]
    charts: Dict[str, DummyChartSpecDict]


class DummyChartParamsDict(TypedDict):
    categories: List[str]
    series: Dict[str, Dict[str, Union[int, float]]]


@dataclass
class DummyParams(Params[DummySpec]):
    variables: Dict[str, str]
    charts: Dict[str, DummyChartParamsDict]


class DummyTemplate(Template[DummyParams]):
    def render_to_file(self, params: DummyParams, file_object: IO[bytes]) -> None:
        file_object.write(repr(params).encode())


class DummyFiller(Filler[DummySpec, DummyParams, DummyTemplate]):
    params_cls = DummyParams


@pytest.fixture
def dummy_spec():
    return DummySpec(
        variables={"item_id": "item.id", "item_price": "item.price|format_currency"},
        charts={
            "views_chart": {
                "categories": "stats.views|keys",
                "series": {"views": "stats.views"},
            }
        },
    )


@pytest.fixture
def dummy_data():
    return {
        "item": {"id": "12345", "price": 84.95},
        "stats": {"views": {"monday": 22, "tuesday": 33}},
    }


@pytest.fixture
def dummy_params(dummy_data):
    return DummyParams(
        variables={
            "item_id": dummy_data["item"]["id"],
            "item_price": str(
                format_currency_filter(dummy_data["item"]["price"], locale="nl_BE")
            ),
        },
        charts={
            "views_chart": {
                "categories": list(dummy_data["stats"]["views"].keys()),
                "series": {"views": dummy_data["stats"]["views"]},
            }
        },
    )


@pytest.fixture
def dummy_template():
    return DummyTemplate("/bogus/path")


@pytest.fixture
def dummy_filler(dummy_spec: DummySpec, dummy_data):
    return DummyFiller(dummy_spec, dummy_data, locale="nl_BE")


def test_params(dummy_params: DummyParams, dummy_spec: DummySpec):
    dummy_params.validate_spec(dummy_spec)


def test_template(dummy_template: DummyTemplate, dummy_params: DummyParams):
    assert dummy_template.render(dummy_params) == repr(dummy_params).encode()


def test_filler(
    dummy_filler: DummyFiller, dummy_template: DummyTemplate, dummy_params: DummyParams
):
    assert dummy_filler.fill(dummy_template) == repr(dummy_params).encode()
