from __future__ import annotations
import typing as t
from pydantic import field_validator, RootModel
from .common import ImmutableBaseModel, faker_wordlist, Seq
from .generators import RandGen, RandState
from abc import ABC, abstractmethod

T = t.TypeVar("T", covariant=True)


class GenCfgBase(ImmutableBaseModel, ABC, t.Generic[T]):
    @property
    @abstractmethod
    def return_type(self) -> t.Type[T]:
        ...

    @abstractmethod
    def build(self) -> RandGen[T]:
        ...


class Word(GenCfgBase[str]):
    type: t.Literal["word"] = "word"

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> RandGen[str]:
        def fn(state: RandState) -> str:
            return state.rnd.choice(faker_wordlist(state.locale))
        return fn


class Integer(GenCfgBase[int]):
    type: t.Literal["integer"] = "integer"
    min: int = -1000
    max: int = 1000

    @property
    def return_type(self) -> t.Type[int]:
        return int

    def build(self) -> RandGen[int]:
        def fn(state: RandState) -> int:
            return state.rnd.randint(self.min, self.max)
        return fn


class Maybe(GenCfgBase[t.Optional[T]]):
    type: t.Literal["maybe"] = "maybe"
    prob: float = 0.5
    child: GenCfgProxy[T]

    @property
    def return_type(self) -> t.Type[t.Optional[T]]:
        return t.Optional[self.child.return_type]

    def build(self) -> RandGen[t.Optional[T]]:
        child_gen = self.child.build()

        def fn(state: RandState) -> t.Optional[T]:
            if state.rnd.random() < self.prob:
                return child_gen(state)
            else:
                return None
        return fn


def local_unique(gen: RandGen[T]) -> RandGen[T]:
    seen: t.Set[T] = set()

    def fn(state: RandState) -> T:
        for _ in range(state.max_unique_attempts):
            value = gen(state)
            if value not in seen:
                seen.add(value)
                return value
        raise RuntimeError(
            f"Could not generate local unique value with {state.max_unique_attempts} attempts"
        )
    return fn


class Batch(GenCfgBase[Seq[T]]):
    type: t.Literal["batch"] = "batch"
    child: GenCfgProxy[T]
    size: int | t.Tuple[int, int]
    unique: bool = False

    @property
    def return_type(self) -> t.Type[Seq[T]]:
        return Seq[self.child.return_type]

    def build(self) -> RandGen[Seq[T]]:
        child_gen = self.child.build()

        if self.unique:
            child_gen = local_unique(child_gen)

        def fn(state: RandState) -> Seq[T]:
            if isinstance(self.size, int):
                size = self.size
            else:
                size = state.rnd.randint(*self.size)

            return tuple(child_gen(state) for _ in range(size))
        return fn


class Unique(GenCfgBase[T]):
    type: t.Literal["unique"] = "unique"
    child: GenCfgProxy[T]

    @property
    def return_type(self) -> t.Type[T]:
        return self.child.return_type

    def build(self) -> RandGen[T]:
        child_gen = self.child.build()

        def fn(state: RandState) -> T:
            for _ in range(state.max_unique_attempts):
                value = child_gen(state)
                if value not in state.seen:
                    state.seen.add(value)
                    return value
            raise RuntimeError(
                f"Could not generate global unique value with {state.max_unique_attempts} attempts"
            )
        return fn


GenCfg = Word | Integer | Batch[t.Any] | Maybe[t.Any] | Unique[t.Any]


def parse_gencfg(raw: t.Any) -> GenCfg:
    from pydantic import TypeAdapter
    return TypeAdapter(GenCfg).validate_python(raw)


class GenCfgProxy(RootModel[GenCfg], t.Generic[T]):
    @field_validator('root')
    @classmethod
    def validate_gencfg(cls, v: GenCfg) -> GenCfg:
        # https://github.com/pydantic/pydantic/issues/7837
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
        child_gen = self.root.build()

        def fn(state: RandState) -> T:
            result = child_gen(state)
            assert isinstance(result, self.return_type)
            return result
        return fn
