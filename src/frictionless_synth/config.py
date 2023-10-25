from __future__ import annotations
import typing as t
from pydantic import field_validator, RootModel, Field as PydanticField
from .common import ImmutableBaseModel, TupleSeq
from . import generators as gen
from . import models as m
from abc import ABC, abstractmethod

T = t.TypeVar("T", covariant=True)


class GenCfgBase(ImmutableBaseModel, ABC, t.Generic[T]):
    @property
    @abstractmethod
    def return_type(self) -> t.Type[T]:
        ...

    @abstractmethod
    def build(self) -> gen.RandGen[T]:
        ...

# Word generators


class Word(GenCfgBase[str]):
    type: t.Literal["word"] = "word"

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.word()


class Sentence(GenCfgBase[str]):
    type: t.Literal["sentence"] = "sentence"
    n_words: int | t.Tuple[int, int] = 10

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.joined_words(gen.join_sentence, self.n_words)


class SnakeCaseName(GenCfgBase[str]):
    type: t.Literal["snake_case_name"] = "snake_case_name"
    n_words: int | t.Tuple[int, int] = (1, 3)

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.joined_words(gen.join_snake_case, self.n_words)


class CamelCaseName(GenCfgBase[str]):
    type: t.Literal["camel_case_name"] = "camel_case_name"
    n_words: int | t.Tuple[int, int] = (1, 3)

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.joined_words(gen.join_camel_case, self.n_words)


class KebabCaseName(GenCfgBase[str]):
    type: t.Literal["kebab_case_name"] = "kebab_case_name"
    n_words: int | t.Tuple[int, int] = (1, 3)

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.joined_words(gen.join_kebab_case, self.n_words)


class SnakeCaseCapsName(GenCfgBase[str]):
    type: t.Literal["snake_case_caps_name"] = "snake_case_caps_name"
    n_words: int | t.Tuple[int, int] = (1, 3)

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.joined_words(gen.join_snake_case_caps, self.n_words)


class MissingValueName(GenCfgBase[str]):
    type: t.Literal["missing_value_name"] = "missing_value_name"

    @property
    def return_type(self) -> t.Type[str]:
        return str

    def build(self) -> gen.RandGen[str]:
        return gen.missing_value()

# Numeric generators


class Integer(GenCfgBase[int]):
    type: t.Literal["integer"] = "integer"
    min: int = 0
    max: int = 1000

    @property
    def return_type(self) -> t.Type[int]:
        return int

    def build(self) -> gen.RandGen[int]:
        return gen.integer(self.min, self.max)


# Generator combinators


class Maybe(GenCfgBase[t.Optional[T]]):
    type: t.Literal["maybe"] = "maybe"
    prob: float = 0.5
    child: GenCfgProxy[T]

    @property
    def return_type(self) -> t.Type[t.Optional[T]]:
        return t.Optional[self.child.return_type]

    def build(self) -> gen.RandGen[t.Optional[T]]:
        return gen.maybe(self.child.build(), self.prob)


class Choice(GenCfgBase[T]):
    type: t.Literal["choice"] = "choice"
    children: TupleSeq[GenCfgProxy[T]]

    @property
    def return_type(self) -> t.Type[T]:
        if not self.children:
            raise ValueError("Choice must have at least one child")

        result = self.children[0].return_type
        for child in self.children[1:]:
            result = t.Union[result, child.return_type]

        return result

    def build(self) -> gen.RandGen[T]:
        child_gens = tuple(child.build() for child in self.children)
        return gen.choice(child_gens)


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

    def build(self) -> gen.RandGen[TupleSeq[T]]:
        child_gens = tuple(child.build() for child in self.children)

        if self.unique:
            child_gens = tuple(
                gen.local_unique(child_gen) for child_gen in child_gens
            )

        return gen.seq(child_gens)


class Batch(GenCfgBase[TupleSeq[T]]):
    type: t.Literal["batch"] = "batch"
    child: GenCfgProxy[T]
    size: int | t.Tuple[int, int]
    unique: bool = False

    @property
    def return_type(self) -> t.Type[TupleSeq[T]]:
        return TupleSeq[self.child.return_type]

    def build(self) -> gen.RandGen[TupleSeq[T]]:
        child_gen = self.child.build()
        return gen.batch(child_gen, self.size, self.unique)


class Unique(GenCfgBase[T]):
    type: t.Literal["unique"] = "unique"
    child: GenCfgProxy[T]

    @property
    def return_type(self) -> t.Type[T]:
        return self.child.return_type

    def build(self) -> gen.RandGen[T]:
        child_gen = self.child.build()
        return gen.unique(child_gen)


def build_helper(gen: GenCfgProxy[T] | T) -> gen.RandGen[T]:
    if isinstance(gen, GenCfgProxy):
        return gen.build()
    else:
        def fn(state: gen.RandState) -> T:
            return gen
        return fn

# Frictionless Generators


def default_gencfg_field(*lazy_options: t.Callable[[], GenCfgBase[T]]) -> GenCfgProxy[T]:
    if len(lazy_options) == 1:
        return PydanticField(default_factory=lambda: GenCfgProxy[T](root=t.cast(GenCfg, lazy_options[0]())))
    else:
        return PydanticField(default_factory=lambda: GenCfgProxy[T](root=Choice[t.Any](children=tuple((
            GenCfgProxy[T](root=t.cast(GenCfg, option())) for option in lazy_options
        )))))


class IntegerFieldType(GenCfgBase[m.IntegerFieldType]):
    type: t.Literal["integer_field_type"] = "integer_field_type"
    required_prob: float = 0.5
    unique_prob: float = 0.5
    undefined_prob: float = 0.5
    minimum_range: t.Tuple[int, int] = (0, 1000)
    maximum_range: t.Tuple[int, int] = (0, 1000)
    missing_value_name: GenCfgProxy[str] = default_gencfg_field(
        MissingValueName
    )
    missing_value_length_max: int = 5

    @property
    def return_type(self) -> t.Type[m.IntegerFieldType]:
        return m.IntegerFieldType

    def build(self) -> gen.RandGen[m.IntegerFieldType]:
        required_gen = gen.maybe(
            gen.boolean(self.required_prob),
            1 - self.undefined_prob,
        )
        unique_gen = gen.maybe(
            gen.boolean(self.unique_prob),
            1 - self.undefined_prob,
        )
        minimum_gen = gen.maybe(
            gen.integer(*self.minimum_range),
            1 - self.undefined_prob,
        )
        maximum_gen = gen.maybe(
            gen.integer(*self.maximum_range),
            1 - self.undefined_prob,
        )
        missing_value_name_gen = build_helper(self.missing_value_name)
        missing_value_gen = gen.maybe(
            gen.batch(
                missing_value_name_gen,
                (0, self.missing_value_length_max),
                unique=True,
            ),
            1 - self.undefined_prob
        )
        return gen.integer_field_type(
            required=required_gen,
            unique=unique_gen,
            minimum=minimum_gen,
            maximum=maximum_gen,
            missingValues=missing_value_gen,
        )


class EnumIntegerFieldType(GenCfgBase[m.EnumIntegerFieldType]):
    type: t.Literal["enum_integer_field_type"] = "enum_integer_field_type"
    level_start_range: t.Tuple[int, int] = (2, 10)
    n_levels_range: t.Tuple[int, int] = (2, 10)
    label_name: GenCfgProxy[str] = default_gencfg_field(SnakeCaseCapsName)
    no_label_prob: float = 0.2
    required_prob: float = 0.5
    unique_prob: float = 0.5
    ordered_prob: float = 0.5
    undefined_prob: float = 0.5
    missing_value_name: GenCfgProxy[str] = default_gencfg_field(
        MissingValueName
    )
    missing_value_length_max: int = 5

    @property
    def return_type(self) -> t.Type[m.EnumIntegerFieldType]:
        return m.EnumIntegerFieldType

    def build(self) -> gen.RandGen[m.EnumIntegerFieldType]:
        value_range_gen = gen.interval(
            start=gen.integer(*self.level_start_range),
            size=gen.integer(*self.n_levels_range),
        )

        required_gen = gen.maybe(
            gen.boolean(self.required_prob),
            1 - self.undefined_prob,
        )

        unique_gen = gen.maybe(
            gen.boolean(self.unique_prob),
            1 - self.undefined_prob,
        )

        ordered_gen = gen.maybe(
            gen.boolean(self.ordered_prob),
            1 - self.undefined_prob,
        )

        label_name_gen = build_helper(self.label_name)
        missing_value_name_gen = build_helper(self.missing_value_name)

        missing_value_gen = gen.maybe(
            gen.batch(
                missing_value_name_gen,
                (0, self.missing_value_length_max),
                unique=True,
            ),
            1 - self.undefined_prob
        )

        return gen.enum_integer_field_type(
            value_range=value_range_gen,
            label_name=label_name_gen,
            no_label_prob=self.no_label_prob,
            required=required_gen,
            unique=unique_gen,
            ordered=ordered_gen,
            missingValues=missing_value_gen,
        )


class NumberFieldType(GenCfgBase[m.NumberFieldType]):
    type: t.Literal["number_field_type"] = "number_field_type"
    required_prob: float = 0.5
    unique_prob: float = 0.5
    undefined_prob: float = 0.5
    minimum_range: t.Tuple[int, int] = (0, 1000)
    maximum_range: t.Tuple[int, int] = (0, 1000)
    missing_value_name: GenCfgProxy[str] = default_gencfg_field(
        MissingValueName
    )
    missing_value_length_max: int = 5

    @property
    def return_type(self) -> t.Type[m.NumberFieldType]:
        return m.NumberFieldType

    def build(self) -> gen.RandGen[m.NumberFieldType]:
        required_gen = gen.maybe(
            gen.boolean(self.required_prob),
            1 - self.undefined_prob,
        )
        unique_gen = gen.maybe(
            gen.boolean(self.unique_prob),
            1 - self.undefined_prob,
        )
        minimum_gen = gen.maybe(
            gen.integer(*self.minimum_range),
            1 - self.undefined_prob,
        )
        maximum_gen = gen.maybe(
            gen.integer(*self.maximum_range),
            1 - self.undefined_prob,
        )
        missing_value_name_gen = build_helper(self.missing_value_name)
        missing_value_gen = gen.maybe(
            gen.batch(
                missing_value_name_gen,
                (0, self.missing_value_length_max),
                unique=True,
            ),
            1 - self.undefined_prob
        )
        return gen.number_field_type(
            required=required_gen,
            unique=unique_gen,
            minimum=minimum_gen,
            maximum=maximum_gen,
            missingValues=missing_value_gen,
        )


class StringFieldType(GenCfgBase[m.StringFieldType]):
    type: t.Literal["string_field_type"] = "string_field_type"
    required_prob: float = 0.5
    unique_prob: float = 0.5
    undefined_prob: float = 0.5
    minLength_range: t.Tuple[int, int] = (0, 20)
    maxLength_range: t.Tuple[int, int] = (10, 30)
    missing_value_name: GenCfgProxy[str] = default_gencfg_field(
        MissingValueName
    )
    missing_value_length_max: int = 5

    @property
    def return_type(self) -> t.Type[m.StringFieldType]:
        return m.StringFieldType

    def build(self) -> gen.RandGen[m.StringFieldType]:
        required_gen = gen.maybe(
            gen.boolean(self.required_prob),
            1 - self.undefined_prob,
        )
        unique_gen = gen.maybe(
            gen.boolean(self.unique_prob),
            1 - self.undefined_prob,
        )
        minLength_gen = gen.maybe(
            gen.integer(*self.minLength_range),
            1 - self.undefined_prob,
        )
        maxLength_gen = gen.maybe(
            gen.integer(*self.maxLength_range),
            1 - self.undefined_prob,
        )
        missing_value_name_gen = build_helper(self.missing_value_name)
        missing_value_gen = gen.maybe(
            gen.batch(
                missing_value_name_gen,
                (0, self.missing_value_length_max),
                unique=True,
            ),
            1 - self.undefined_prob
        )
        return gen.string_field_type(
            required=required_gen,
            unique=unique_gen,
            minLength=minLength_gen,
            maxLength=maxLength_gen,
            missingValues=missing_value_gen,
        )


class EnumStringFieldType(GenCfgBase[m.EnumStringFieldType]):
    type: t.Literal["enum_string_field_type"] = "enum_string_field_type"
    label_name: GenCfgProxy[str] = default_gencfg_field(SnakeCaseCapsName)
    n_levels_range: t.Tuple[int, int] = (2, 10)
    required_prob: float = 0.5
    unique_prob: float = 0.5
    ordered_prob: float = 0.5
    undefined_prob: float = 0.5
    missing_value_name: GenCfgProxy[str] = default_gencfg_field(
        MissingValueName
    )
    missing_value_length_max: int = 5

    @property
    def return_type(self) -> t.Type[m.EnumStringFieldType]:
        return m.EnumStringFieldType

    def build(self) -> gen.RandGen[m.EnumStringFieldType]:
        required_gen = gen.maybe(
            gen.boolean(self.required_prob),
            1 - self.undefined_prob,
        )

        unique_gen = gen.maybe(
            gen.boolean(self.unique_prob),
            1 - self.undefined_prob,
        )

        ordered_gen = gen.maybe(
            gen.boolean(self.ordered_prob),
            1 - self.undefined_prob,
        )

        label_name_gen = build_helper(self.label_name)

        label_names_gen = gen.batch(
            label_name_gen,
            self.n_levels_range,
            unique=True,
        )

        missing_value_name_gen = build_helper(self.missing_value_name)

        missing_value_gen = gen.maybe(
            gen.batch(
                missing_value_name_gen,
                (0, self.missing_value_length_max),
                unique=True,
            ),
            1 - self.undefined_prob
        )

        return gen.enum_string_field_type(
            levels=label_names_gen,
            required=required_gen,
            unique=unique_gen,
            ordered=ordered_gen,
            missingValues=missing_value_gen,
        )


class MetaGroup(GenCfgBase[TupleSeq[m.FieldMeta]]):
    type: t.Literal["meta_group"] = "meta_group"
    group_name: GenCfgProxy[str] = default_gencfg_field(CamelCaseName)
    n_range: t.Tuple[int, int] = (3, 15)
    field_name: GenCfgProxy[str] = default_gencfg_field(CamelCaseName)
    title: GenCfgProxy[str] = default_gencfg_field(Sentence)
    description: GenCfgProxy[str] = default_gencfg_field(Sentence)
    undefined_prob: float = 0.5

    @property
    def return_type(self) -> t.Type[TupleSeq[m.FieldMeta]]:
        return TupleSeq[m.FieldMeta]

    def build(self) -> gen.RandGen[TupleSeq[m.FieldMeta]]:
        group_name_gen = gen.unique(build_helper(self.group_name))

        title_gen = gen.maybe(
            build_helper(self.title),
            1 - self.undefined_prob
        )
        description_gen = gen.maybe(
            build_helper(self.description),
            1 - self.undefined_prob
        )

        def fn(state: gen.RandState) -> TupleSeq[m.FieldMeta]:
            group_name = group_name_gen(state)

            name_gen = gen.local_unique(gen.mapper(
                build_helper(self.field_name),
                lambda x: group_name + "_" + x,
            ))

            meta_gen = gen.field_meta(name_gen, title_gen, description_gen)

            meta_field_gen = gen.batch(
                meta_gen,
                self.n_range,
                unique=False,
            )

            return meta_field_gen(state)

        return fn


class FieldGroup(GenCfgBase[TupleSeq[m.Field[m.FieldType]]]):
    type: t.Literal["field_group"] = "field_group"
    group_meta: GenCfgProxy[TupleSeq[m.FieldMeta]] = default_gencfg_field(
        MetaGroup
    )
    field_type: GenCfgProxy[m.FieldType] = default_gencfg_field(
        IntegerFieldType,
        EnumIntegerFieldType,
        NumberFieldType,
        StringFieldType,
        EnumStringFieldType,
    )

    @property
    def return_type(self) -> t.Type[TupleSeq[m.Field[m.FieldType]]]:
        return TupleSeq[m.Field[m.FieldType]]

    def build(self) -> gen.RandGen[TupleSeq[m.Field[m.FieldType]]]:
        group_meta_gen = build_helper(self.group_meta)
        field_type_gen = build_helper(self.field_type)

        return gen.field_group(
            group_meta_gen,
            field_type_gen,
        )


class LikertFieldGroup(GenCfgBase[TupleSeq[m.Field[m.FieldType]]]):
    type: t.Literal["likert_field_group"] = "likert_field_group"
    group_meta: GenCfgProxy[TupleSeq[m.FieldMeta]] = default_gencfg_field(
        MetaGroup
    )
    field_type: GenCfgProxy[m.IntegerFieldType] = default_gencfg_field(
        IntegerFieldType,
    )

    @property
    def return_type(self) -> t.Type[TupleSeq[m.Field[m.FieldType]]]:
        return TupleSeq[m.Field[m.FieldType]]

    def build(self) -> gen.RandGen[TupleSeq[m.Field[m.FieldType]]]:
        group_meta_gen = build_helper(self.group_meta)
        field_type_gen = build_helper(self.field_type)

        return gen.field_group(
            group_meta_gen,
            field_type_gen,
        )


class TableSchema(GenCfgBase[m.TableSchema]):
    type: t.Literal["table_schema"] = "table_schema"
    fields: GenCfgProxy[TupleSeq[m.Field[m.FieldType]]] | TupleSeq[GenCfgProxy[TupleSeq[m.Field[m.FieldType]]]] = default_gencfg_field(
        FieldGroup,
    )
    n_rows_range: t.Tuple[int, int] = (10, 1000)
    missing_value_name: GenCfgProxy[str] = default_gencfg_field(
        MissingValueName
    )
    missing_value_length_max: int = 5
    undefined_prob: float = 0.5

    @property
    def return_type(self) -> t.Type[m.TableSchema]:
        return m.TableSchema

    def build(self) -> gen.RandGen[m.TableSchema]:
        if isinstance(self.fields, GenCfgProxy):
            fields_gen = build_helper(self.fields)
        else:
            fields_gen = gen.seq_flat(
                tuple(build_helper(field) for field in self.fields)
            )

        missing_value_name_gen = build_helper(self.missing_value_name)

        missing_value_gen = gen.maybe(
            gen.batch(
                missing_value_name_gen,
                (0, self.missing_value_length_max),
                unique=True,
            ),
            1 - self.undefined_prob
        )

        n_rows_gen = gen.integer(*self.n_rows_range)

        return gen.table_schema(
            fields_gen,
            missing_value_gen,
            n_rows_gen,
        )


class TableResource(GenCfgBase[m.TableResource]):
    type: t.Literal["table_resource"] = "table_resource"
    name: GenCfgProxy[str] = default_gencfg_field(KebabCaseName)
    description: GenCfgProxy[str] = default_gencfg_field(Sentence)
    table_schema: GenCfgProxy[m.TableSchema] = default_gencfg_field(
        TableSchema
    )

    @property
    def return_type(self) -> t.Type[m.TableResource]:
        return m.TableResource

    def build(self) -> gen.RandGen[m.TableResource]:
        name_gen = build_helper(self.name)
        description_gen = build_helper(self.description)
        table_schema_gen = build_helper(self.table_schema)

        return gen.table_resource(
            name_gen,
            description_gen,
            table_schema_gen,
        )


class Package(GenCfgBase[m.Package]):
    type: t.Literal["package"] = "package"
    name: GenCfgProxy[str] = default_gencfg_field(KebabCaseName)
    description: GenCfgProxy[str] = default_gencfg_field(Sentence)
    resource: GenCfgProxy[m.TableResource] = default_gencfg_field(
        TableResource,
    )
    n_resources: int | t.Tuple[int, int] = (1, 5)

    @property
    def return_type(self) -> t.Type[m.Package]:
        return m.Package

    def build(self) -> gen.RandGen[m.Package]:
        name_gen = build_helper(self.name)
        description_gen = build_helper(self.description)
        resources_gen = gen.batch(
            build_helper(self.resource),
            self.n_resources,
            unique=False,
        )

        return gen.package(
            name_gen,
            description_gen,
            resources_gen,
        )


# All generators
GenCfg = (
    Word |
    Integer |
    Sentence |
    SnakeCaseName |
    CamelCaseName |
    KebabCaseName |
    SnakeCaseCapsName |
    IntegerFieldType |
    EnumIntegerFieldType |
    NumberFieldType |
    MissingValueName |
    StringFieldType |
    EnumStringFieldType |
    Batch[t.Any] |
    Maybe[t.Any] |
    Unique[t.Any] |
    Seq[t.Any] |
    Choice[t.Any] |
    FieldGroup |
    LikertFieldGroup |
    MetaGroup |
    TableSchema |
    TableResource |
    Package
)


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

        if not is_subset_type(gencfg_return_type, class_generic_type):
            raise ValueError(
                f"Expected child return type {class_generic_type} but got {gencfg_return_type}")

        return v

    @property
    def return_type(self) -> t.Type[T]:
        arg: t.Any = self.root.return_type
        return arg

    def build(self) -> gen.RandGen[T]:
        child_gen = self.root.build()

        def fn(state: gen.RandState) -> T:
            result: t.Any = child_gen(state)
            return result
        return fn
