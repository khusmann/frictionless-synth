from __future__ import annotations
import typing as t
from pydantic import field_validator, RootModel
from .common import ImmutableBaseModel, faker_wordlist, TupleSeq
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


class Interval(GenCfgBase[t.Tuple[int, int]]):
    type: t.Literal["interval"] = "interval"
    start_min: int
    start_max: int
    length_min: int
    length_max: int

    @property
    def return_type(self) -> t.Type[t.Tuple[int, int]]:
        return t.Tuple[int, int]

    def build(self) -> RandGen[t.Tuple[int, int]]:
        def fn(state: RandState) -> t.Tuple[int, int]:
            start = state.rnd.randint(self.start_min, self.start_max)
            length = state.rnd.randint(self.length_min, self.length_max)
            return (start, start + length)
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


class Seq(GenCfgBase[TupleSeq[T]]):
    type: t.Literal["seq"] = "seq"
    children: TupleSeq[GenCfgProxy[T]]
    unique: bool = False

    @property
    def return_type(self) -> t.Type[TupleSeq[T]]:
        if not self.children:
            raise ValueError("Seq must have at least one child")

        result = self.children[0].return_type
        for child in self.children[1:]:
            result = t.Union[result, child.return_type]

        return TupleSeq[result]

    def build(self) -> RandGen[TupleSeq[T]]:
        child_gens = tuple(child.build() for child in self.children)

        if self.unique:
            child_gens = tuple(
                local_unique(child_gen) for child_gen in child_gens
            )

        def fn(state: RandState) -> TupleSeq[T]:
            return tuple(child_gen(state) for child_gen in child_gens)
        return fn


class Batch(GenCfgBase[TupleSeq[T]]):
    type: t.Literal["batch"] = "batch"
    child: GenCfgProxy[T]
    size: int | t.Tuple[int, int]
    unique: bool = False

    @property
    def return_type(self) -> t.Type[TupleSeq[T]]:
        return TupleSeq[self.child.return_type]

    def build(self) -> RandGen[TupleSeq[T]]:
        child_gen = self.child.build()

        if self.unique:
            child_gen = local_unique(child_gen)

        def fn(state: RandState) -> TupleSeq[T]:
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


GenCfg = Word | Integer | Batch[t.Any] | Maybe[t.Any] | Unique[t.Any] | Seq[t.Any] | Interval


def parse_gencfg(raw: t.Any) -> GenCfg:
    from pydantic import TypeAdapter
    return TypeAdapter(GenCfg).validate_python(raw)


def is_subset_type(a: t.Type[t.Any], b: t.Type[t.Any]) -> bool:
    if a is b:
        return True
    if t.get_origin(a) is t.Union:
        return all(is_subset_type(x, b) for x in t.get_args(a))
    if t.get_origin(b) is t.Union:
        return any(is_subset_type(a, x) for x in t.get_args(b))
    if t.get_origin(a):
        # a is a generic type
        return a is b

    return issubclass(a, b)


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

        print(gencfg_return_type)
        print(class_generic_type)

        if not is_subset_type(gencfg_return_type, class_generic_type):
            raise ValueError(
                f"Expected child return type {class_generic_type} but got {gencfg_return_type}")

        return v

    @property
    def return_type(self) -> t.Type[T]:
        arg: t.Any = self.root.return_type
        return arg

    def build(self) -> RandGen[T]:
        child_gen = self.root.build()

        def fn(state: RandState) -> T:
            result: t.Any = child_gen(state)
            return result
        return fn
