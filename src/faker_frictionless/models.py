from __future__ import annotations
from dataclasses import dataclass
import typing as t
from .common import Seq


class FieldMeta(t.NamedTuple):
    name: str
    title: t.Optional[str] = None
    description: t.Optional[str] = None


class IntegerFieldType(t.NamedTuple):
    required: t.Optional[bool] = None
    unique: t.Optional[bool] = None
    minimum: t.Optional[int] = None
    maximum: t.Optional[int] = None
    missingValues: t.Optional[Seq[str]] = None


class EnumIntegerLevel(t.NamedTuple):
    value: int | str
    label: t.Optional[str] = None


class EnumIntegerFieldType(t.NamedTuple):
    levels: Seq[EnumIntegerLevel]
    required: t.Optional[bool] = None
    unique: t.Optional[bool] = None
    ordered: t.Optional[bool] = None
    missingValues: t.Optional[Seq[str]] = None


class NumberFieldType(t.NamedTuple):
    required: t.Optional[bool] = None
    unique: t.Optional[bool] = None
    minimum: t.Optional[float] = None
    maximum: t.Optional[float] = None
    missingValues: t.Optional[Seq[str]] = None


# Note: Not including EnumNumberFieldType for now

class StringFieldType(t.NamedTuple):
    required: t.Optional[bool] = None
    unique: t.Optional[bool] = None
    minLength: t.Optional[int] = None
    maxLength: t.Optional[int] = None
    pattern: t.Optional[str] = None
    missingValues: t.Optional[Seq[str]] = None


class EnumStringFieldType(t.NamedTuple):
    levels: Seq[str]
    required: t.Optional[bool] = None
    unique: t.Optional[bool] = None
    ordered: t.Optional[bool] = None
    missingValues: t.Optional[Seq[str]] = None


FieldType = IntegerFieldType | EnumIntegerFieldType | NumberFieldType | StringFieldType | EnumStringFieldType

FieldT = t.TypeVar("FieldT", bound=FieldType)


@dataclass(frozen=True)
class Field(t.Generic[FieldT]):
    meta: FieldMeta
    type: FieldT


class Measure(t.NamedTuple):
    name: str
    items: Seq[Field[FieldType]]
    # TODO: composites
