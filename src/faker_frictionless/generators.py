from __future__ import annotations
import typing as t
from random import Random
from .common import faker_wordlist
from . import models as m

T = t.TypeVar("T")
P = t.TypeVar("P")

T_num = t.TypeVar("T_num", int, float)

MissingValueStyle = t.Literal["SPSS", "SATA", "UNDERSCORE"]


class RandState(t.NamedTuple):
    rnd: Random = Random()
    locale: str = "en-US"
    seen: t.Set[t.Any] = set()
    max_unique_attempts: int = 1000
    default_maybe_prob: float = 0.5
    default_missing_style: MissingValueStyle | RandGen[str] = "SPSS"


RandGen = t.Callable[[RandState], T]


def integer(min: int = -1000, max: int = 1000) -> RandGen[int]:
    def fn(state: RandState) -> int:
        return state.rnd.randint(min, max)
    return fn


def interval(start: RandGen[T_num] = integer(), size: RandGen[T_num] = integer()) -> RandGen[t.Tuple[T_num, T_num]]:
    def fn(state: RandState) -> t.Tuple[T_num, T_num]:
        min = start(state)
        return (min, min + size(state))
    return fn


def number(min: float = -1000.0, max: float = 1000.0) -> RandGen[float]:
    def fn(state: RandState) -> float:
        return state.rnd.uniform(min, max)
    return fn


def boolean(prob: float = 0.5) -> RandGen[bool]:
    def fn(state: RandState) -> bool:
        return state.rnd.random() < prob
    return fn


def word() -> RandGen[str]:
    def fn(state: RandState) -> str:
        return state.rnd.choice(faker_wordlist(state.locale))
    return fn


def batch(gen: RandGen[T], size: int, unique: bool = False) -> RandGen[t.List[T]]:
    def fn(state: RandState) -> t.List[T]:
        local_gen = local_unique(gen) if unique else gen
        return [local_gen(state) for _ in range(size)]
    return fn


def vbatch(gen: RandGen[T], min_size: int, max_size: int, unique: bool = False) -> RandGen[t.List[T]]:
    def fn(state: RandState) -> t.List[T]:
        return batch(gen, state.rnd.randint(min_size, max_size), unique)(state)
    return fn


def map_rg(gen: RandGen[T], map_fn: t.Callable[[T], P]) -> RandGen[P]:
    def fn(state: RandState) -> P:
        return map_fn(gen(state))
    return fn


def maybe(gen: RandGen[T], prob: t.Optional[float] = None) -> RandGen[t.Optional[T]]:
    def fn(state: RandState) -> t.Optional[T]:
        p = prob if prob is not None else state.default_maybe_prob
        if state.rnd.random() < p:
            return gen(state)
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


def unique(gen: RandGen[T]) -> RandGen[T]:
    def fn(state: RandState) -> T:
        for _ in range(state.max_unique_attempts):
            value = gen(state)
            if value not in state.seen:
                state.seen.add(value)
                return value
        raise RuntimeError(
            f"Could not generate unique value with {state.max_unique_attempts} attempts"
        )
    return fn


def sentence(n_words: int = 6, wordgen: RandGen[str] = word()) -> RandGen[str]:
    def fn(state: RandState) -> str:
        words = batch(wordgen, n_words)(state)
        words[0] = words[0].title()
        return " ".join(words) + "."
    return fn


NameJoiner = t.Callable[[t.Sequence[str]], str]


def join_camel_case(words: t.Sequence[str]) -> str:
    head = words[0].lower()
    tail = "".join(word.title() for word in words[1:])
    return head + tail


def join_snake_case(words: t.Sequence[str]) -> str:
    return "_".join(word.lower() for word in words)


def join_kebab_case(words: t.Sequence[str]) -> str:
    return "-".join(word.lower() for word in words)


def join_snake_case_caps(words: t.Sequence[str]) -> str:
    return join_snake_case(words).upper()


def varname(
    joiner: NameJoiner = join_camel_case,
    max_words: int = 3,
    wordgen: RandGen[str] = word()
) -> RandGen[str]:
    def fn(state: RandState) -> str:
        return joiner(batch(wordgen, state.rnd.randint(1, max_words))(state))
    return unique(fn)


##################################################################

def field_meta(
    name: RandGen[str] = unique(varname()),
    title: RandGen[t.Optional[str]] = maybe(sentence()),
    description: RandGen[t.Optional[str]] = maybe(sentence()),
) -> RandGen[m.FieldMeta]:
    def fn(state: RandState) -> m.FieldMeta:
        return m.FieldMeta(
            name=name(state),
            title=title(state),
            description=description(state),
        )
    return fn


def enum_level_name() -> RandGen[str]:
    def fn(state: RandState) -> str:
        return varname(join_snake_case_caps)(state)
    return fn


def integer_field_type(
    required: RandGen[t.Optional[bool]] = maybe(boolean()),
    unique: RandGen[t.Optional[bool]] = maybe(boolean()),
    minimum: RandGen[t.Optional[int]] = maybe(integer()),
    maximum: RandGen[t.Optional[int]] = maybe(integer()),
    missingValues: RandGen[
        t.Optional[t.Sequence[str]]
    ] = maybe(vbatch(enum_level_name(), 0, 3, unique=True)),
) -> RandGen[m.IntegerFieldType]:
    def fn(state: RandState) -> m.IntegerFieldType:
        return m.IntegerFieldType(
            required=required(state),
            unique=unique(state),
            minimum=minimum(state),
            maximum=maximum(state),
            missingValues=missingValues(state),
        )
    return fn


def spss_missing_value() -> RandGen[str]:
    def fn(state: RandState) -> str:
        return str(integer(-1000, -1)(state))
    return fn


def stata_missing_value() -> RandGen[str]:
    from string import ascii_lowercase

    def fn(state: RandState) -> str:
        return state.rnd.choice([
            "." + i for i in ascii_lowercase
        ])
    return fn


def underscore_missing_value(label: RandGen[str] = enum_level_name()) -> RandGen[str]:
    def fn(state: RandState) -> str:
        return "_" + label(state) + "_"
    return fn


def missing_value(
    style: t.Optional[MissingValueStyle | RandGen[str]] = None,
) -> RandGen[str]:
    def fn(state: RandState) -> str:
        s = state.default_missing_style if style is None else style

        if not isinstance(s, str):
            return s(state)

        match s:
            case "SPSS":
                return spss_missing_value()(state)
            case "SATA":
                return stata_missing_value()(state)
            case "UNDERSCORE":
                return underscore_missing_value()(state)
    return fn


def enum_integer_levels(
    value_range: RandGen[t.Tuple[int, int]] = interval(
        start=integer(0, 10),
        size=integer(2, 5),
    ),
    label: RandGen[t.Optional[str]] = maybe(enum_level_name()),
    missingValues: t.Sequence[str] = [],
    no_label_prob: float = 0.5,
) -> RandGen[t.Sequence[m.EnumIntegerLevel]]:
    def fn(state: RandState) -> t.Sequence[m.EnumIntegerLevel]:
        values = (
            *range(*value_range(state)),
            *missingValues
        )
        if state.rnd.random() < no_label_prob:
            return [m.EnumIntegerLevel(value) for value in values]
        else:
            local_label = local_unique(label)
            return [
                m.EnumIntegerLevel(value, label=local_label(state))
                for value in values
            ]

    return fn


def enum_integer_field_type(
    levels: RandGen[t.Sequence[m.EnumIntegerLevel]] = enum_integer_levels(),
    required: RandGen[t.Optional[bool]] = maybe(boolean()),
    unique: RandGen[t.Optional[bool]] = maybe(boolean()),
    ordered: RandGen[t.Optional[bool]] = maybe(boolean()),
    missingValues: RandGen[
        t.Optional[t.Sequence[str]]
    ] = maybe(vbatch(missing_value(), 0, 3, unique=True)),
) -> RandGen[m.EnumIntegerFieldType]:
    def fn(state: RandState) -> m.EnumIntegerFieldType:
        return m.EnumIntegerFieldType(
            levels=levels(state),
            required=required(state),
            unique=unique(state),
            ordered=ordered(state),
            missingValues=missingValues(state),
        )
    return fn


def number_field_type(
    required: RandGen[t.Optional[bool]] = maybe(boolean()),
    unique: RandGen[t.Optional[bool]] = maybe(boolean()),
    minimum: RandGen[t.Optional[float]] = maybe(number()),
    maximum: RandGen[t.Optional[float]] = maybe(number()),
    missingValues: RandGen[
        t.Optional[t.Sequence[str]]
    ] = maybe(vbatch(missing_value(), 0, 3, unique=True)),
) -> RandGen[m.NumberFieldType]:
    def fn(state: RandState) -> m.NumberFieldType:
        return m.NumberFieldType(
            required=required(state),
            unique=unique(state),
            minimum=minimum(state),
            maximum=maximum(state),
            missingValues=missingValues(state),
        )
    return fn


def pattern_constraint() -> RandGen[str]:
    return word()  # TODO


def string_field_type(
    required: RandGen[t.Optional[bool]] = maybe(boolean()),
    unique: RandGen[t.Optional[bool]] = maybe(boolean()),
    minLength: RandGen[t.Optional[int]] = maybe(integer(0, 10)),
    maxLength: RandGen[t.Optional[int]] = maybe(integer(0, 10)),
    pattern: RandGen[t.Optional[str]] = maybe(pattern_constraint()),
    missingValues: RandGen[
        t.Optional[t.Sequence[str]]
    ] = maybe(vbatch(missing_value(), 0, 3, unique=True)),
) -> RandGen[m.StringFieldType]:
    def fn(state: RandState) -> m.StringFieldType:
        l1 = minLength(state)
        l2 = maxLength(state)
        return m.StringFieldType(
            required=required(state),
            unique=unique(state),
            minLength=min(l1, l2) if (
                l1 is not None and l2 is not None
            ) else l1,
            maxLength=max(l1, l2) if (
                l1 is not None and l2 is not None
            ) else l2,
            pattern=pattern(state),
            missingValues=missingValues(state),
        )
    return fn


def enum_string_field_type(
    levels: RandGen[t.Sequence[str]] = vbatch(
        enum_level_name(), 2, 5, unique=True
    ),
    required: RandGen[t.Optional[bool]] = maybe(boolean()),
    unique: RandGen[t.Optional[bool]] = maybe(boolean()),
    ordered: RandGen[t.Optional[bool]] = maybe(boolean()),
    missingValues: RandGen[
        t.Optional[t.Sequence[str]]
    ] = maybe(vbatch(missing_value(), 0, 3, unique=True)),
) -> RandGen[m.EnumStringFieldType]:
    def fn(state: RandState) -> m.EnumStringFieldType:
        return m.EnumStringFieldType(
            levels=levels(state),
            required=required(state),
            unique=unique(state),
            ordered=ordered(state),
            missingValues=missingValues(state),
        )
    return fn
