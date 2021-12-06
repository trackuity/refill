from __future__ import annotations

import functools
import json
import urllib.request
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from typing import IO, Any, Callable, Dict, List, Type, Union, get_type_hints

from pyparsing import (
    Group,
    Optional,
    QuotedString,
    Word,
    alphanums,
    alphas,
    delimited_list,
)
from typing_extensions import get_args, get_origin

from .filters import Filters, default_filters


Selector = str

JSONNumber = Union[int, float]
JSONValue = Union[JSONNumber, str, bool, None, Dict[str, Any], List[Any]]
JSONArray = List[JSONValue]
JSONObject = Dict[str, JSONValue]


lookup_token = "=" + Word(alphas + "_", alphanums + "_").set_results_name("lookup")

field_token = Word(alphas + "_", alphanums + "_").set_results_name(
    "fields", list_all_matches=True
)
selection_token = Group(field_token + ("." + field_token)[0, ...]).set_results_name(
    "selections", list_all_matches=True
)

argument_token = Word(alphanums) | QuotedString("'", esc_quote="''")
filter_token = "|" + Group(
    Word(alphas + "_", alphanums + "_").set_results_name("name")
    + Optional("(" + Optional(delimited_list(argument_token), [])("arguments") + ")")
).set_results_name("filters", list_all_matches=True)

combine_token = delimited_list(selection_token, delim=",")
filtered_token = lookup_token | selection_token | ("(" + combine_token + ")")
unfiltered_token = lookup_token | combine_token
selector_parser = (filtered_token + filter_token[1, ...]) | unfiltered_token


def parse_selector(selector: Selector):
    return selector_parser.parse_string(selector, parse_all=True)


def select_data(
    data: Dict[str, Any],
    selector: Selector,
    *,
    filters: Filters = default_filters,
    lookup_table: dict[str, Any] = None,
    locale: str = "en_US",
    urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
):
    locale = locale.replace("-", "_")  # babel wants underscores, not dashes

    parsed = parse_selector(selector)

    if parsed.lookup:
        if lookup_table is None:
            raise ValueError("lookup table required but not provided")
        selected = lookup_table[parsed.lookup]
    else:
        selecteds = []
        for selection in parsed.selections:
            selected = data
            for field in selection.fields:
                if isinstance(selected, list):
                    selected = [item[field] for item in selected]
                elif isinstance(selected, dict):
                    selected = selected[field]
                else:
                    raise ValueError(f"unexpected type in given data: {type(selected)}")
            selecteds.append(selected)

        def combine_into_dict(x, y):
            for k, v in y.items():
                x[k].append(v)
            return x

        def combine_into_list(x, y):
            x.append(y)
            return x

        if len(selecteds) == 1:
            selected = selecteds[0]
        elif all(isinstance(s, dict) for s in selecteds):
            selected = functools.reduce(combine_into_dict, selecteds, defaultdict(list))
        else:
            selected = functools.reduce(combine_into_list, selecteds, [])

    for parsed_filter in parsed.filters:
        selected = filters.apply(
            selected,
            parsed_filter.name,
            parsed_filter.arguments,
            locale=locale,
            urlopen=urlopen,
        )

    return selected


def apply_spec(
    spec: JSONObject,
    data: Dict[str, Any],
    *,
    filters: Filters = default_filters,
    locale: str = "en_US",
    urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
) -> Dict[str, Any]:
    result: JSONObject = {}
    for key, value in spec.items():
        if isinstance(value, str):
            ignore_key_errors = False
            if key.endswith("?"):
                key = key[:-1]
                ignore_key_errors = True
            try:
                result[key] = select_data(
                    data,
                    value,
                    filters=filters,
                    lookup_table=result,
                    locale=locale,
                    urlopen=urlopen,
                )
            except KeyError:
                if not ignore_key_errors:
                    raise
        elif isinstance(value, dict):
            result[key] = apply_spec(
                value, data, filters=filters, locale=locale, urlopen=urlopen
            )
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

    def apply(
        self,
        data: Dict[str, Any],
        *,
        filters: Filters = default_filters,
        locale: str = "en_US",
        urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
    ) -> Dict[str, Any]:
        return apply_spec(
            self.to_dict(), data, filters=filters, locale=locale, urlopen=urlopen
        )

    def validate(self, target_cls: Type, globalns=None, localns=None) -> None:
        validate_spec(self.to_dict(), target_cls, globalns, localns)
