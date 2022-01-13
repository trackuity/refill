from __future__ import annotations

import datetime
import inspect
import re
import urllib.request
from copy import deepcopy
from itertools import accumulate, islice
from typing import IO, Any, Callable, Dict, List

from babel.dates import format_date
from babel.numbers import format_currency, format_decimal, format_percent


class Filters:
    def __init__(self) -> None:
        self._functions: Dict[str, Callable] = {}

    def copy(self):
        return deepcopy(self)

    def apply(
        self,
        data: Any,
        name: str,
        arguments: List[Any],
        *,
        locale: str = "en_US",
        urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
    ) -> Any:
        func = self._functions[name]

        parameters = inspect.signature(func).parameters
        args = [
            eval(param.annotation)(arg)  # eval type annotation to get class
            for (param, arg) in zip(islice(parameters.values(), 1, None), arguments)
            if param.kind != inspect.Parameter.KEYWORD_ONLY
        ]

        kwargs = {}
        if "locale" in parameters:
            kwargs["locale"] = locale
        if "urlopen" in parameters:
            kwargs["urlopen"] = urlopen

        try:
            return func(data, *args, **kwargs)
        except KeyError:
            raise ValueError(f"filter '{name}' does not exist")
        except TypeError:
            raise ValueError(f"invalid arguments for filter '{name}': {arguments}")

    def register(self, name: str, function: Callable) -> None:
        self._functions[name] = function

    def __call__(self, function: Callable) -> Callable:
        self.register(re.sub(r"_filter$", "", function.__name__), function)
        return function


default_filters = Filters()


@default_filters
def keys_filter(x):
    if isinstance(x, dict):
        return list(x.keys())
    elif isinstance(x, list):
        return list(range(len(x)))
    else:
        raise ValueError("keys filter cannot be applied to given value")


@default_filters
def values_filter(x):
    if isinstance(x, dict):
        return list(x.values())
    elif isinstance(x, list):
        return x
    else:
        raise ValueError("values filter cannot be applied to given value")


@default_filters
def sort_filter(x):
    if isinstance(x, list):
        return sorted(x)
    elif isinstance(x, dict):
        return dict(sorted(x.items()))
    else:
        raise ValueError("sort filter cannot be applied to given value")


@default_filters
def reverse_filter(x):
    if isinstance(x, list):
        return list(reversed(x))
    elif isinstance(x, dict):
        return dict(reversed(list(x.items())))
    elif isinstance(x, str):
        return x[::-1]
    else:
        raise ValueError("reverse filter cannot be applied to given value")


@default_filters
def lower_filter(x):
    if isinstance(x, str):
        return x.lower()
    elif isinstance(x, list):
        return list(lower_filter(i) for i in x)
    elif isinstance(x, dict):
        return {k: lower_filter(v) for (k, v) in x.items()}
    else:
        raise ValueError("lower filter cannot be applied to given value")


@default_filters
def upper_filter(x):
    if isinstance(x, str):
        return x.upper()
    elif isinstance(x, list):
        return list(upper_filter(i) for i in x)
    elif isinstance(x, dict):
        return {k: upper_filter(v) for (k, v) in x.items()}
    else:
        raise ValueError("upper filter cannot be applied to given value")


@default_filters
def str_filter(x, encoding: str = None):
    return str(x) if encoding is None else str(x, encoding=encoding)


@default_filters
def int_filter(x):
    return int(x)


@default_filters
def selfie_filter(x):
    if isinstance(x, str) or isinstance(x, int) or isinstance(x, float):
        return {x: x}
    elif isinstance(x, list):
        return dict(zip(x, x))
    else:
        raise ValueError("selfie filter cannot be applied to given value")


@default_filters
def first_filter(x):
    if isinstance(x, list):
        return x[0]
    else:
        raise ValueError("first filter cannot be applied to given value")


@default_filters
def last_filter(x):
    if isinstance(x, list):
        return x[-1]
    else:
        raise ValueError("last filter cannot be applied to given value")


@default_filters
def head_filter(x, n: int = 1):
    if isinstance(x, list):
        return x[:n]
    elif isinstance(x, dict):
        return dict(islice(x.items(), n))
    else:
        raise ValueError("head filter cannot be applied to given value")


@default_filters
def tail_filter(x, n: int = 1):
    if isinstance(x, list):
        return x[-n:]
    elif isinstance(x, dict):
        return dict(list(x.items())[-n:])
    else:
        raise ValueError("tail filter cannot be applied to given value")


@default_filters
def sum_filter(x):
    if isinstance(x, list):
        return sum(x)
    elif isinstance(x, dict):
        return {k: sum_filter(v) for (k, v) in x.items()}
    else:
        raise ValueError("sum filter cannot be applied to given value")


@default_filters
def cumul_filter(x):
    if isinstance(x, list):
        return list(accumulate(x))
    elif isinstance(x, dict):
        return dict(zip(x.keys(), accumulate(x.values())))
    else:
        raise ValueError("cumul filter cannot be applied to given value")


@default_filters
def format_number_filter(x, *, locale: str):
    if isinstance(x, int) or isinstance(x, float):
        return format_decimal(x, locale=locale)
    elif isinstance(x, list):
        return [format_number_filter(i, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {k: format_number_filter(v, locale=locale) for (k, v) in x.items()}
    else:
        raise ValueError("format_number filter cannot be applied to given value")


@default_filters
def format_currency_filter(x, currency: str = "USD", *, locale: str):
    if isinstance(x, int) or isinstance(x, float):
        return format_currency(x, currency, locale=locale)
    elif isinstance(x, list):
        return [format_currency_filter(i, currency, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {k: format_currency_filter(v, locale=locale) for (k, v) in x.items()}
    else:
        raise ValueError("format_currency filter cannot be applied to given value")


@default_filters
def format_percent_filter(x, format: str = None, *, locale: str):
    if isinstance(x, int) or isinstance(x, float):
        return format_percent(x, format, locale=locale)
    elif isinstance(x, list):
        return [format_percent_filter(i, format, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {
            k: format_percent_filter(v, format, locale=locale) for (k, v) in x.items()
        }
    else:
        raise ValueError("format_percent filter cannot be applied to given value")


@default_filters
def format_date_filter(x, format: str = "medium", *, locale: str):
    if isinstance(x, datetime.date) or isinstance(x, datetime.datetime):
        return format_date(x, format, locale=locale)
    elif isinstance(x, str):
        if 4 <= len(x) < 10:
            missing_count = 10 - len(x)
            x = x + "-01-01"[-missing_count:]  # support YYYY and YYYY-MM too
        return format_date(datetime.datetime.fromisoformat(x), format, locale=locale)
    elif isinstance(x, list):
        return [format_date_filter(i, format, locale=locale) for i in x]
    elif isinstance(x, dict):
        return {k: format_date_filter(v, format, locale=locale) for (k, v) in x.items()}
    else:
        raise ValueError("format_date filter cannot be applied to given value")


@default_filters
def fetch_filter(x, *, urlopen: Callable[[str], IO[bytes]]):
    if isinstance(x, str):
        return urlopen(x).read()
    elif isinstance(x, list):
        return [urlopen(i).read() for i in x]
    else:
        raise ValueError("fetch filter cannot be applied to given value")
