from __future__ import annotations
import typing as t
from pydantic_core import CoreSchema, core_schema
from pydantic import GetCoreSchemaHandler, BaseModel

from .common import ImmutableBaseModel
from .generators import RandGen, RandState

T = t.TypeVar("T", covariant=True)


ALL_GENCFG: t.List[t.Type[GenCfg[t.Any]]] = []


class GenCfg(t.Protocol, t.Generic[T]):
    def build(self) -> RandGen[T]: ...

    @property
    def return_type(self) -> t.Type[T]: ...

    @classmethod
    def model_validate(cls, obj: t.Any) -> GenCfg[T]: ...

    @classmethod
    def __get_pydantic_core_schema__(
        cls, __source: t.Type[BaseModel], __handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return_type = t.get_args(__source)[0]
        return core_schema.no_info_before_validator_function(
            gencfg_before_validate(return_type), core_schema.any_schema()
        )


def gencfg_before_validate(return_type: t.Any):
    def fn(v: t.Any) -> t.Any:
        for i in ALL_GENCFG:
            try:
                result = i.model_validate(v)
                if result.return_type == return_type:
                    return result
            except:
                pass
            raise ValueError(
                f"Could not find a generator config for {return_type}"
            )
        return v
    return fn


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
    gen: GenCfg[T]
    prob: float = 0.5

    @property
    def return_type(self) -> t.Type[t.Optional[T]]:
        return self.gen.return_type

    def build(self) -> RandGen[t.Optional[T]]:
        def fn(state: RandState) -> t.Optional[T]:
            if state.rnd.random() < self.prob:
                return self.gen.build()(state)
            else:
                return None
        return fn


ALL_GENCFG.extend([
    Word,
    Integer,
    Maybe[t.Any],
])
