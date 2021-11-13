from __future__ import annotations
from typing import (
    Any,
    Dict,
    List,
    Type,
    Union,
    TYPE_CHECKING,
    get_type_hints,
)
from typing_extensions import get_args, get_origin
from dataclasses import asdict, dataclass

import json

from pyparsing import Word, alphas, alphanums


Selector = str

JSONNumber = Union[int, float]
JSONValue = Union[JSONNumber, str, bool, None, Dict[str, Any], List[Any]]
JSONArray = List[JSONValue]
JSONObject = Dict[str, JSONValue]


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
        elif isinstance(selected, dict):
            selected = selected[field]
        else:
            raise ValueError(f"unexpected type in given data: {type(selected)}")

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
    result: JSONObject = {}
    for key, value in spec.items():
        if isinstance(value, str):
            result[key] = select_data(data, value)
        elif isinstance(value, dict):
            result[key] = apply_spec(data, value)
        else:
            raise ValueError(f"unexpected type in given data: {type(value)}")
    return result


def validate_spec(
    target_cls: Type, spec: JSONObject, globalns=None, localns=None
) -> None:
    hints = get_type_hints(target_cls, globalns, localns)
    diff = set(hints.keys()).symmetric_difference(set(spec.keys()))
    if diff:
        raise ValueError(f"missing and/or superfluous key(s) in {target_cls}: {diff}")
    for name, sub_spec in spec.items():
        hint = hints[name]
        args = get_args(hint)
        if isinstance(sub_spec, str):
            assert all(arg in (str, int, float, JSONNumber) for arg in args)
        elif get_origin(hint) is dict:
            assert isinstance(sub_spec, dict)
            for value in sub_spec.values():
                if isinstance(value, str):
                    assert all(
                        arg in (str, int, float, JSONNumber)
                        for arg in get_args(args[1])
                    )
                else:
                    validate_spec(args[1], value)
        else:
            raise ValueError(
                f"unexpected type hint encountered in {target_cls}: {hint}"
            )


@dataclass
class Spec:
    variables: Dict[str, Selector]

    @classmethod
    def from_dict(cls, json_dict: JSONObject) -> Spec:
        return cls(**json_dict)  # type: ignore

    def to_dict(self) -> JSONObject:
        return asdict(self)

    @classmethod
    def from_json(cls, json_str: str) -> Spec:
        return cls.from_dict(json.loads(json_str))

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def apply(self, data: JSONObject) -> JSONObject:
        return apply_spec(data, self.to_dict())

    def validate(self, target_cls: Type, globalns=None, localns=None) -> None:
        validate_spec(target_cls, self.to_dict(), globalns, localns)
