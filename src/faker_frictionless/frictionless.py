import typing as t
from .common import ImmutableBaseModel
from polyfactory.factories.pydantic_factory import ModelFactory


def joinCamelCase(words: t.Iterable[str]) -> str:
    return "".join(word.capitalize() if idx != 0 else word for idx, word in enumerate(words))


class FieldInfo(ImmutableBaseModel):
    name: str
    title: t.Optional[str] = None
    description: t.Optional[str] = None
    required: t.Optional[bool] = None
    unique: t.Optional[bool] = None
    missingValues: t.Optional[t.List[str]] = None


class FieldInfoFactory(ModelFactory[FieldInfo]):
    __model__ = FieldInfo

    @classmethod
    def name(cls) -> str:
        return joinCamelCase([
            cls.__faker__.unique.word("verb"),
            *cls.__faker__.unique.words(2, "noun"),
        ])

    @classmethod
    def title(cls) -> t.Optional[str]:
        return cls.__faker__.sentence() if cls.__faker__.boolean(20) else None

    @classmethod
    def description(cls) -> t.Optional[str]:
        return cls.__faker__.paragraph() if cls.__faker__.boolean(20) else None

    @classmethod
    def required(cls) -> t.Optional[bool]:
        return cls.__faker__.boolean(20)

    @classmethod
    def unique(cls) -> t.Optional[bool]:
        return cls.__faker__.boolean(20)

    @classmethod
    def missingValues(cls) -> t.Optional[t.List[str]]:
        return [w.upper() for w in cls.__faker__.words(cls.__random__.randrange(0, 3), "noun")] if cls.__faker__.boolean(20) else None


class IntegerField(ImmutableBaseModel):
    minimum: t.Optional[int] = None
    maximum: t.Optional[int] = None


class IntegerFieldFactory(ModelFactory[IntegerField]):
    __model__ = IntegerField

    @classmethod
    def minimum(cls) -> t.Optional[int]:
        return cls.__faker__.random_int(-100, 100) if cls.__faker__.boolean(10) else None

    @classmethod
    def maximum(cls) -> t.Optional[int]:
        return cls.__faker__.random_int(-100, 100) if cls.__faker__.boolean(10) else None


class IntegerEnumLevel(ImmutableBaseModel):
    value: int
    label: t.Optional[str] = None


class EnumIntegerField(ImmutableBaseModel):
    levels: t.List[IntegerEnumLevel]
    ordered: t.Optional[bool] = None
    valueLabelStyle: t.Optional[t.Literal["SPSS", "STATA"]] = None


class EnumIntegerFieldFactory(ModelFactory[EnumIntegerField]):
    __model__ = EnumIntegerField

    @classmethod
    def levels(cls) -> t.List[IntegerEnumLevel]:

        return [
            IntegerEnumLevel(value=cls.__faker__.random_int(-100, 100), label=cls.__faker__.sentence()) for _ in range(cls.__random__.randrange(1, 10))
        ]

    @classmethod
    def required(cls) -> t.Optional[bool]:
        return cls.__faker__.boolean(20)

    @classmethod
    def unique(cls) -> t.Optional[bool]:
        return cls.__faker__.boolean(20)

    @classmethod
    def ordered(cls) -> t.Optional[bool]:
        return cls.__faker__.boolean(20)

    @classmethod
    def valueLabelStyle(cls) -> t.Optional[t.Literal["SPSS", "STATA"]]:
        return cls.__faker__.random_element(["SPSS", "STATA"]) if cls.__faker__.boolean(20) else None
