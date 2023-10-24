from __future__ import annotations
import typing as t
from pydantic import field_validator
from .common import ImmutableBaseModel
from .generators import RandGen, RandState

T = t.TypeVar("T", covariant=True)


class Word(ImmutableBaseModel):
    type: t.Literal["word"] = "word"
    return_type: t.Final = str

    def build(self) -> RandGen[str]:
        def fn(state: RandState) -> str:
            return "hello"
        return fn


class Integer(ImmutableBaseModel):
    type: t.Literal["integer"] = "integer"
    return_type: t.Final = int
    minimum: int = -1000
    maximum: int = 1000

    def build(self) -> RandGen[int]:
        def fn(state: RandState) -> int:
            return state.rnd.randint(self.minimum, self.maximum)
        return fn


def validate_child_gencfg(cls: t.Type[ImmutableBaseModel], v: GenCfg) -> GenCfg:
    from pydantic._internal._generics import get_args
    class_generic_type = get_args(cls)[0]
    gencfg_return_type = v.return_type

    if class_generic_type is t.Any:
        # If the class generic is Any, then we don't care about the return type
        return v

    if t.get_origin(gencfg_return_type):
        # If the gencfg return type is a generic, then we look for an identical match
        # between the gencfg return type and the class generic type
        if class_generic_type != gencfg_return_type:
            raise ValueError(
                f"Maybe child expected return type {class_generic_type} but got {gencfg_return_type}")
    else:
        # If the gencfg return type is a regular type, then we look for a subclass match
        if isinstance(gencfg_return_type, class_generic_type):
            return v
    return v


class Maybe(ImmutableBaseModel, t.Generic[T]):
    type: t.Literal["maybe"] = "maybe"
    prob: float = 0.5
    child: GenCfg
    validate_gencfg = field_validator('child')(validate_child_gencfg)

    @property
    def return_type(self) -> t.Type[t.Optional[T]]:
        arg: t.Any = self.child.return_type
        return t.Optional[arg]

    def build(self) -> RandGen[t.Optional[T]]:
        def fn(state: RandState) -> t.Optional[T]:
            if state.rnd.random() < self.prob:
                result = self.child.build()(state)
                assert isinstance(result, self.return_type)
                return result
            else:
                return None
        return fn


GenCfg = Maybe[t.Any] | Word | Integer
