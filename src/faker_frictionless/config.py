from __future__ import annotations
import typing as t
from pydantic import field_validator, RootModel
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


class Maybe(ImmutableBaseModel, t.Generic[T]):
    type: t.Literal["maybe"] = "maybe"
    prob: float = 0.5
    child: GenCfgProxy[T]

    @property
    def return_type(self) -> t.Type[t.Optional[T]]:
        return t.Optional[self.child.return_type]

    def build(self) -> RandGen[t.Optional[T]]:
        def fn(state: RandState) -> t.Optional[T]:
            if state.rnd.random() < self.prob:
                return self.child.build()(state)
            else:
                return None
        return fn


GenCfg = Maybe[t.Any] | Word | Integer


class GenCfgProxy(RootModel[GenCfg], t.Generic[T]):
    @field_validator('root')
    @classmethod
    def validate_gencfg(cls, v: GenCfg) -> GenCfg:
        from pydantic._internal._generics import get_args

        class_args = get_args(cls)

        if not class_args:
            # If the class is not called with generic args, then we don't care about the return type
            return v

        class_generic_type = class_args[0]
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

    @property
    def return_type(self) -> t.Type[T]:
        arg: t.Any = self.root.return_type
        return arg

    def build(self) -> RandGen[T]:
        def fn(state: RandState) -> T:
            result = self.root.build()(state)
            assert isinstance(result, self.return_type)
            return result
        return fn
