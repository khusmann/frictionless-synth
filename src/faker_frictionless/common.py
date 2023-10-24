from __future__ import annotations
import typing as t
from pydantic import BaseModel
from pathlib import Path
from pydantic import BaseModel, TypeAdapter, ValidationError

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

yamlReader = YAML(typ='base')

yamlWriter = YAML()


class ImmutableBaseModel(BaseModel):
    class Config:
        frozen = True

    @classmethod
    def read_yaml(cls, path: Path):
        return parse_yaml_as(cls, path)

    def write_yaml(self, path: Path, exclude_none: bool = True):
        with open(path, "w") as f:
            yamlWriter.dump(self.model_dump(exclude_none=exclude_none), f)


def parse_yaml_as(model_type: t.Type[_T], path: Path) -> _T:
    try:
        obj = yamlReader.load(path.read_text())
    except YAMLError as e:
        raise ValueError(f"Error parsing yaml in {path}") from e

    try:
        return TypeAdapter(model_type).validate_python(obj)
    except ValidationError as e:
        raise ValueError(f"Error validating yaml in {path}") from e


def faker_wordlist(locale: str) -> t.Sequence[str]:
    from importlib import import_module
    locale = locale.replace("-", "_")
    module_path = ".".join(["faker", "providers", "lorem", locale])
    module = import_module(module_path)
    return module.Provider.word_list


_T = t.TypeVar("_T")

TupleSeq = t.Tuple[_T, ...]
