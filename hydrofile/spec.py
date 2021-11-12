from __future__ import annotations
from typing import Dict, List, Union, TYPE_CHECKING
from typing_extensions import Protocol

from pyparsing import Word, alphas, alphanums


Selector = str

if TYPE_CHECKING:
    # nasty trickery to make recursive JSON types possible
    # cfr. https://github.com/python/typing/issues/182#issuecomment-966151818

    class JSONArray(List[JSONValue], Protocol):  # type: ignore
        __class__: Type[List[JSONValue]]  # type: ignore

    class JSONObject(Dict[str, JSONValue], Protocol):  # type: ignore
        __class__: Type[Dict[str, JSONValue]]  # type: ignore

    JSONValue = Union[None, int, float, str, JSONArray, JSONObject]


field_token = Word(alphas + "_", alphanums + "_").setResultsName(
    "fields", listAllMatches=True
)
filter_token = "|" + Word(alphas + "_", alphanums + "_").setResultsName(
    "filters", listAllMatches=True
)
selector_parser = field_token + ("." + field_token)[0, ...] + filter_token[0, ...]  # type: ignore


def parse_selector(selector: Selector):
    return selector_parser.parseString(selector)


def select_data(data: JSONObject, selector: Selector) -> JSONValue:
    parsed = parse_selector(selector)

    selected = data
    for field in parsed.fields:
        if isinstance(selected, list):
            selected = [item[field] for item in selected]
        else:
            selected = selected[field]

    for filter_ in parsed.filters:
        try:
            selected = {"keys": keys_filter, "keys_unsorted": keys_unsorted_filter}[
                filter_
            ](selected)
        except KeyError:
            raise ValueError(f"filter '{parsed.filter}' does not exist")

    return selected


def keys_filter(x: JSONValue) -> JSONArray:
    if isinstance(x, dict):
        return sorted(x.keys())
    elif isinstance(x, list):
        return list(range(len(x)))
    else:
        raise ValueError("filter cannot be applied to given value")


def keys_unsorted_filter(x: JSONValue) -> JSONArray:
    if isinstance(x, dict):
        return list(x.keys())
    elif isinstance(x, list):
        return list(range(len(x)))
    else:
        raise ValueError("filter cannot be applied to given value")


def apply_spec(data: JSONObject, spec: JSONObject) -> JSONObject:
    result = {}
    for key, value in spec.items():
        if isinstance(value, str):
            result[key] = select_data(data, value)
        else:
            result[key] = apply_spec(data, value)
    return result
