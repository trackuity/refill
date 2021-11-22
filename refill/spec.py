from __future__ import annotations

import functools
import inspect
import json
import urllib.request
from dataclasses import asdict, is_dataclass
from itertools import islice
from typing import IO, Any, Callable, Dict, List, Type, Union, get_type_hints

from babel.numbers import format_currency, format_decimal, format_percent
from pyparsing import Group, Optional, Word, alphanums, alphas, delimitedList
from typing_extensions import get_args, get_origin


Selector = str

JSONNumber = Union[int, float]
JSONValue = Union[JSONNumber, str, bool, None, Dict[str, Any], List[Any]]
JSONArray = List[JSONValue]
JSONObject = Dict[str, JSONValue]


field_token = Word(alphas + "_", alphanums + "_").setResultsName(
    "fields", listAllMatches=True
)
selection_token = Group(field_token + ("." + field_token)[0, ...]).setResultsName(  # type: ignore
    "selections", listAllMatches=True
)
filter_token = "|" + Group(
    Word(alphas + "_", alphanums + "_").setResultsName("name")
    + Optional("(" + Optional(delimitedList(Word(alphanums)), [])("arguments") + ")")  # type: ignore
).setResultsName("filters", listAllMatches=True)
selector_parser = delimitedList(selection_token, delim="+") + filter_token[0, ...]  # type: ignore


def parse_selector(selector: Selector):
    return selector_parser.parseString(selector)


def select_data(
    data: Dict[str, Any],
    selector: Selector,
    *,
    locale: str = "en_US",
    urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
):
    locale = locale.replace("-", "_")  # babel wants underscores, not dashes

    parsed = parse_selector(selector)

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

    def combine(x, y):
        if isinstance(x, list) and isinstance(y, list):
            return x + y
        elif isinstance(x, dict) and isinstance(y, dict):
            return {**x, **y}
        else:
            raise ValueError(f"cannot combine {x} and {y}")

    selected = functools.reduce(combine, selecteds)

    for filter_ in parsed.filters:
        try:
            func = {
                "keys": keys_filter,
                "values": values_filter,
                "sort": sort_filter,
                "reverse": reverse_filter,
                "lower": lower_filter,
                "upper": upper_filter,
                "str": str_filter,
                "int": int_filter,
                "first": first_filter,
                "last": last_filter,
                "head": head_filter,
                "tail": tail_filter,
                "sum": sum_filter,
                "format_number": format_number_filter,
                "format_currency": format_currency_filter,
                "format_percent": format_percent_filter,
                "fetch": fetch_filter,
            }[filter_.name]
            parameters = inspect.signature(func).parameters
            args = [
                eval(param.annotation)(arg)  # eval type annotation to get class
                for (param, arg) in zip(
                    islice(parameters.values(), 1, None), filter_.arguments
                )
                if param.kind != inspect.Parameter.KEYWORD_ONLY
            ]
            kwargs = {}
            if "locale" in parameters:
                kwargs["locale"] = locale
            if "urlopen" in parameters:
                kwargs["urlopen"] = urlopen
            selected = func(selected, *args, **kwargs)
        except KeyError:
            raise ValueError(f"filter '{filter_}' does not exist")
        except TypeError:
            raise ValueError(
                f"invalid arguments for filter '{filter_}': {filter_.arguments}"
            )

    return selected


def keys_filter(x):
    if isinstance(x, dict):
        return list(x.keys())
    elif isinstance(x, list):
        return list(range(len(x)))
    else:
        raise ValueError("keys filter cannot be applied to given value")


def values_filter(x):
    if isinstance(x, dict):
        return list(x.values())
    elif isinstance(x, list):
        return x
    else:
        raise ValueError("values filter cannot be applied to given value")


def sort_filter(x):
    if isinstance(x, list):
        return sorted(x)
    else:
        raise ValueError("sort filter cannot be applied to given value")


def reverse_filter(x):
    if isinstance(x, list):
        return list(reversed(x))
    elif isinstance(x, dict):
        return dict(reversed(list(x.items())))
    elif isinstance(x, str):
        return x[::-1]
    else:
        raise ValueError("reverse filter cannot be applied to given value")


def lower_filter(x):
    if isinstance(x, str):
        return x.lower()
    elif isinstance(x, list):
        return list(s.lower() for s in x)
    else:
        raise ValueError("lower filter cannot be applied to given value")


def upper_filter(x):
    if isinstance(x, str):
        return x.upper()
    elif isinstance(x, list):
        return list(s.upper() for s in x)
    else:
        raise ValueError("upper filter cannot be applied to given value")


def str_filter(x, encoding: str = None):
    return str(x) if encoding is None else str(x, encoding=encoding)


def int_filter(x):
    return int(x)


def first_filter(x):
    if isinstance(x, list):
        return x[0]
    else:
        raise ValueError("first filter cannot be applied to given value")


def last_filter(x):
    if isinstance(x, list):
        return x[-1]
    else:
        raise ValueError("last filter cannot be applied to given value")


def head_filter(x, n: int = 1):
    if isinstance(x, list):
        return x[:n]
    elif isinstance(x, dict):
        return dict(islice(x.items(), n))
    else:
        raise ValueError("head filter cannot be applied to given value")


def tail_filter(x, n: int = 1):
    if isinstance(x, list):
        return x[-n:]
    elif isinstance(x, dict):
        return dict(list(x.items())[-n:])
    else:
        raise ValueError("tail filter cannot be applied to given value")


def sum_filter(x):
    if isinstance(x, list):
        return sum(x)
    elif isinstance(x, dict):
        return sum(x.values())
    else:
        raise ValueError("sum filter cannot be applied to given value")


def format_number_filter(x, *, locale: str):
    if isinstance(x, int) or isinstance(x, float):
        return format_decimal(x, locale=locale)
    elif isinstance(x, list):
        return [format_number_filter(i, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {k: format_number_filter(v, locale=locale) for (k, v) in x.items()}
    else:
        raise ValueError("format_number filter cannot be applied to given value")


def format_currency_filter(x, currency: str = "USD", *, locale: str):
    if isinstance(x, int) or isinstance(x, float):
        return format_currency(x, currency, locale=locale)
    elif isinstance(x, list):
        return [format_currency_filter(i, currency, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {k: format_currency_filter(v, locale=locale) for (k, v) in x.items()}
    else:
        raise ValueError("format_currency filter cannot be applied to given value")


def format_percent_filter(x, *, locale: str):
    if isinstance(x, int) or isinstance(x, float):
        return format_percent(x, locale=locale)
    elif isinstance(x, list):
        return [format_percent_filter(i, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {k: format_percent_filter(v, locale=locale) for (k, v) in x.items()}
    else:
        raise ValueError("format_percent filter cannot be applied to given value")


def fetch_filter(x, *, urlopen: Callable[[str], IO[bytes]]):
    if isinstance(x, str):
        return urlopen(x).read()
    elif isinstance(x, list):
        return [urlopen(i).read() for i in x]
    else:
        raise ValueError("fetch filter cannot be applied to given value")


def apply_spec(
    spec: JSONObject,
    data: Dict[str, Any],
    *,
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
                if value.startswith("="):
                    result[key] = result[value[1:]]
                else:
                    result[key] = select_data(
                        data, value, locale=locale, urlopen=urlopen
                    )
            except KeyError:
                if not ignore_key_errors:
                    raise
        elif isinstance(value, dict):
            result[key] = apply_spec(value, data, locale=locale, urlopen=urlopen)
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
        locale: str = "en_US",
        urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
    ) -> Dict[str, Any]:
        return apply_spec(self.to_dict(), data, locale=locale, urlopen=urlopen)

    def validate(self, target_cls: Type, globalns=None, localns=None) -> None:
        validate_spec(self.to_dict(), target_cls, globalns, localns)
