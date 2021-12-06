from __future__ import annotations

import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from io import BytesIO
from typing import IO, Any, Callable, Dict, Generic, Type, TypeVar, Union

import dataclass_utils
import dataclass_utils.error

from .filters import Filters, default_filters
from .spec import Spec


SpecType = TypeVar("SpecType", bound=Spec)


@dataclass
class Params(Generic[SpecType]):
    @classmethod
    def validate_spec(cls, spec: SpecType, globalns=None, localns=None) -> None:
        spec.validate(cls, globalns, localns)


ParamsType = TypeVar("ParamsType", bound=Params)


class Template(ABC, Generic[ParamsType]):
    def __init__(self, path_or_file: Union[str, IO[bytes]]) -> None:
        self._path_or_file = path_or_file

    def render(self, params: ParamsType) -> bytes:
        buffer = BytesIO()
        self.render_to_file(params, buffer)
        return buffer.getvalue()

    @abstractmethod
    def render_to_file(self, params: ParamsType, file_object: IO[bytes]) -> None:
        ...


TemplateType = TypeVar("TemplateType", bound=Template)


class Filler(ABC, Generic[SpecType, ParamsType, TemplateType]):
    params_cls: Type[ParamsType]

    def __init__(
        self,
        spec: SpecType,
        data: Dict[str, Any],
        *,
        filters: Filters = default_filters,
        locale: str = "en_US",
        urlopen: Callable[[str], IO[bytes]] = urllib.request.urlopen,
        globalns=None,
        localns=None,
    ) -> None:
        self.params_cls.validate_spec(spec, globalns, localns)
        self.params = self.params_cls(
            **spec.apply(data, filters=filters, locale=locale, urlopen=urlopen)
        )
        try:
            dataclass_utils.check_type(self.params)
        except dataclass_utils.error.Error as e:
            raise ValueError(str(e))

    def fill(self, template: TemplateType) -> bytes:
        return template.render(self.params)

    def fill_to_file(self, template: TemplateType, file_object: IO[bytes]) -> None:
        return template.render_to_file(self.params, file_object)
