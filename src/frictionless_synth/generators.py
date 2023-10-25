from __future__ import annotations
import typing as t
from random import Random
from .common import faker_wordlist, TupleSeq
from . import models as m

T = t.TypeVar("T")
P = t.TypeVar("P")

MissingValueStyle = t.Literal["SPSS", "SATA", "UNDERSCORE"]


class RandState(t.NamedTuple):
    rnd: Random = Random()
    locale: str = "en-US"
    seen: t.Set[t.Any] = set()
    max_unique_attempts: int = 1000
    default_maybe_prob: float = 0.5
    default_missing_style: MissingValueStyle | RandGen[str] = "SPSS"


RandGen = t.Callable[[RandState], T]

########################
# Primitive & Combinator Generators
########################


def integer(min: int, max: int) -> RandGen[int]:
    def fn(state: RandState) -> int:
        return state.rnd.randint(min, max)
    return fn


def interval(start: RandGen[int], size: RandGen[int]) -> RandGen[t.Tuple[int, int]]:
    def fn(state: RandState) -> t.Tuple[int, int]:
        min = start(state)
        return (min, min + size(state))
    return fn


def number(min: float, max: float) -> RandGen[float]:
    def fn(state: RandState) -> float:
        return state.rnd.uniform(min, max)
    return fn


def boolean(prob: float) -> RandGen[bool]:
    def fn(state: RandState) -> bool:
        return state.rnd.random() < prob
    return fn


def word() -> RandGen[str]:
    def fn(state: RandState) -> str:
        return state.rnd.choice(faker_wordlist(state.locale))
    return fn


def batch(gen: RandGen[T], size: int | t.Tuple[int, int], unique: bool) -> RandGen[TupleSeq[T]]:
    local_gen = local_unique(gen) if unique else gen

    def fn(state: RandState) -> TupleSeq[T]:
        if isinstance(size, int):
            sz = size
        else:
            sz = state.rnd.randint(*size)
        return tuple([local_gen(state) for _ in range(sz)])
    return fn


def seq(gen: TupleSeq[RandGen[T]]) -> RandGen[TupleSeq[T]]:
    def fn(state: RandState) -> TupleSeq[T]:
        return tuple([g(state) for g in gen])
    return fn


def seq_flat(gen: TupleSeq[RandGen[TupleSeq[T]]]) -> RandGen[TupleSeq[T]]:
    return flatten(seq(gen))


def flatten(gen: RandGen[TupleSeq[TupleSeq[T]]]) -> RandGen[TupleSeq[T]]:
    def fn(state: RandState) -> TupleSeq[T]:
        return tuple([item for sublist in gen(state) for item in sublist])
    return fn


def mapper(gen: RandGen[T], map_fn: t.Callable[[T], P]) -> RandGen[P]:
    def fn(state: RandState) -> P:
        return map_fn(gen(state))
    return fn


def maybe(gen: RandGen[T], prob: float) -> RandGen[t.Optional[T]]:
    def fn(state: RandState) -> t.Optional[T]:
        if state.rnd.random() < prob:
            return gen(state)
        else:
            return None
    return fn


def choice(gen: t.Sequence[RandGen[T]]) -> RandGen[T]:
    def fn(state: RandState) -> T:
        return state.rnd.choice([g for g in gen])(state)
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


def join_sentence(words: t.Sequence[str]) -> str:
    head = words[0].title()
    return " ".join([head, *words[1:]]) + "."


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


def joined_words(
    joiner: t.Callable[[t.Sequence[str]], str],
    size: int | t.Tuple[int, int],
) -> RandGen[str]:
    def fn(state: RandState) -> str:
        if isinstance(size, int):
            sz = size
        else:
            sz = state.rnd.randint(*size)
        return mapper(batch(word(), sz, unique=False), joiner)(state)
    return fn


########################
# Model Generators
########################

def field_meta(
    name: RandGen[str],
    title: RandGen[t.Optional[str]],
    description: RandGen[t.Optional[str]],
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
        return joined_words(join_snake_case_caps, (1, 3))(state)
    return fn


def integer_field_type(
    required: RandGen[t.Optional[bool]],
    unique: RandGen[t.Optional[bool]],
    minimum: RandGen[t.Optional[int]],
    maximum: RandGen[t.Optional[int]],
    missingValues: RandGen[t.Optional[TupleSeq[str]]],
) -> RandGen[m.IntegerFieldType]:
    def fn(state: RandState) -> m.IntegerFieldType:
        l1 = minimum(state)
        l2 = maximum(state)
        return m.IntegerFieldType(
            required=required(state),
            unique=unique(state),
            minimum=min(l1, l2) if (
                l1 is not None and l2 is not None
            ) else l1,
            maximum=max(l1, l2) if (
                l1 is not None and l2 is not None
            ) else l2,
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


def underscore_missing_value() -> RandGen[str]:
    label = enum_level_name()

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


def enum_integer_field_type(
    value_range: RandGen[t.Tuple[int, int]],
    label_name: RandGen[t.Optional[str]],
    no_label_prob: float,
    required: RandGen[t.Optional[bool]],
    unique: RandGen[t.Optional[bool]],
    ordered: RandGen[t.Optional[bool]],
    missingValues: RandGen[t.Optional[TupleSeq[str]]],
) -> RandGen[m.EnumIntegerFieldType]:
    local_label = local_unique(label_name)

    def fn(state: RandState) -> m.EnumIntegerFieldType:
        mv = missingValues(state)
        values = (
            *range(*value_range(state)),
            *(mv or []),
        )
        if state.rnd.random() < no_label_prob:
            levels = tuple([m.EnumIntegerLevel(value) for value in values])
        else:
            levels = tuple([
                m.EnumIntegerLevel(value, label=local_label(state))
                for value in values
            ])
        return m.EnumIntegerFieldType(
            levels=levels,
            required=required(state),
            unique=unique(state),
            ordered=ordered(state),
            missingValues=mv,
        )
    return fn


def number_field_type(
    required: RandGen[t.Optional[bool]],
    unique: RandGen[t.Optional[bool]],
    minimum: RandGen[t.Optional[float]],
    maximum: RandGen[t.Optional[float]],
    missingValues: RandGen[t.Optional[TupleSeq[str]]],
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
    required: RandGen[t.Optional[bool]],
    unique: RandGen[t.Optional[bool]],
    minLength: RandGen[t.Optional[int]],
    maxLength: RandGen[t.Optional[int]],
    missingValues: RandGen[
        t.Optional[TupleSeq[str]]
    ],
    pattern: RandGen[t.Optional[str]] = lambda _: None,
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
    levels: RandGen[TupleSeq[str]],
    required: RandGen[t.Optional[bool]],
    unique: RandGen[t.Optional[bool]],
    ordered: RandGen[t.Optional[bool]],
    missingValues: RandGen[
        t.Optional[TupleSeq[str]]
    ],
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


def field_group(
    meta_group: RandGen[TupleSeq[m.FieldMeta]],
    type: RandGen[m.FieldType],
):
    def fn(state: RandState):
        return tuple(
            m.Field[m.FieldType](
                meta=met,
                type=type(state),
            ) for met in meta_group(state)
        )
    return fn


def table_schema(
    fields: RandGen[TupleSeq[m.Field[m.FieldType]]],
    missingValues: RandGen[t.Optional[TupleSeq[str]]],
    n_rows: RandGen[int],
):
    def fn(state: RandState) -> m.TableSchema:
        return m.TableSchema(
            fields=fields(state),
            missingValues=missingValues(state),
            n_rows=n_rows(state),
        )
    return fn


def table_resource(
    name: RandGen[str],
    description: RandGen[t.Optional[str]],
    schema: RandGen[m.TableSchema],
):
    def fn(state: RandState) -> m.TableResource:
        curr_schema = schema(state)
        curr_table_data = table_data(curr_schema)(state)
        return m.TableResource(
            name=name(state),
            description=description(state),
            schema=curr_schema,
            data=curr_table_data,
        )
    return fn


def package(
    name: RandGen[str],
    description: RandGen[t.Optional[str]],
    resources: RandGen[TupleSeq[m.TableResource]],
):
    def fn(state: RandState) -> m.Package:
        return m.Package(
            name=name(state),
            description=description(state),
            resources=resources(state),
        )
    return fn


#################################################

def field_data(field: m.FieldType) -> RandGen[str]:
    import sys

    def fn(state: RandState) -> str:
        match field:
            case m.IntegerFieldType(
                minimum=minimum,
                maximum=maximum,
            ):
                minimum = 0 if minimum is None else minimum
                maximum = sys.maxsize if maximum is None else maximum
                return str(integer(minimum, maximum)(state))
            case m.EnumIntegerFieldType(
                levels=levels,
            ):
                return str(choice([lambda _: l.value for l in levels])(state))
            case m.NumberFieldType(
                minimum=minimum,
                maximum=maximum,
            ):
                minimum = 0 if minimum is None else minimum
                maximum = sys.maxsize if maximum is None else maximum
                return str(number(minimum, maximum)(state))
            case m.StringFieldType():
                return word()(state)
            case m.EnumStringFieldType(
                levels=levels,
            ):
                return choice([lambda _: l for l in levels])(state)
    return fn


def table_data(schema: m.TableSchema) -> RandGen[t.Sequence[t.Mapping[str, str]]]:
    column_names = tuple([f.meta.name for f in schema.fields])
    row_gen = mapper(
        seq(
            tuple(
                field_data(f.type) for f in schema.fields
            )
        ),
        lambda r: dict(zip(column_names, r))
    )

    def fn(state: RandState) -> t.Sequence[t.Mapping[str, str]]:
        return batch(row_gen, schema.n_rows, unique=False)(state)
    return fn
