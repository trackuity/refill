from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Type, Union, get_type_hints

from pyparsing import Word, alphanums, alphas
from typing_extensions import get_args, get_origin


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


def select_data(data: Dict[str, Any], selector: Selector):
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


def keys_filter(x):
    if isinstance(x, dict):
        return sorted(x.keys())
    elif isinstance(x, list):
        return list(range(len(x)))
    else:
        raise ValueError("filter cannot be applied to given value")


def keys_unsorted_filter(x):
    if isinstance(x, dict):
        return list(x.keys())
    elif isinstance(x, list):
        return list(range(len(x)))
    else:
        raise ValueError("filter cannot be applied to given value")


def apply_spec(spec: JSONObject, data: Dict[str, Any]) -> Dict[str, Any]:
    result: JSONObject = {}
    for key, value in spec.items():
        if isinstance(value, str):
            result[key] = select_data(data, value)
        elif isinstance(value, dict):
            result[key] = apply_spec(value, data)
        else:
            raise ValueError(f"unexpected type in given data: {type(value)}")
    return result


def validate_spec(
    spec: JSONObject, target_cls: Type, globalns=None, localns=None
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
                    validate_spec(value, args[1])
        else:
            raise ValueError(
                f"unexpected type hint encountered in {target_cls}: {hint}"
            )


class Spec:
    def __init__(self, **dict_) -> None:
        self._dict = dict_

    @classmethod
    def from_dict(cls, dict_) -> Spec:
        return cls(**dict_)

    def to_dict(self) -> JSONObject:
        if is_dataclass(self):
            return asdict(self)
        else:
            return self._dict

    def __eq__(self, other) -> bool:
        return isinstance(other, Spec) and self.to_dict() == other.to_dict()

    @classmethod
    def from_json(cls, json_: str) -> Spec:
        return cls.from_dict(json.loads(json_))

    def to_json(self):
        return json.dumps(self.to_dict())

    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return apply_spec(self.to_dict(), data)

    def validate(self, target_cls: Type, globalns=None, localns=None) -> None:
        validate_spec(self.to_dict(), target_cls, globalns, localns)
