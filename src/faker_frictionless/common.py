from __future__ import annotations
import typing as t
from pydantic import BaseModel


class ImmutableBaseModel(BaseModel):
    class Config:
        frozen = True


def faker_wordlist(locale: str) -> t.Sequence[str]:
    from importlib import import_module
    locale = locale.replace("-", "_")
    module_path = ".".join(["faker", "providers", "lorem", locale])
    module = import_module(module_path)
    return module.Provider.word_list


_T = t.TypeVar("_T")

Seq = t.Tuple[_T, ...]
