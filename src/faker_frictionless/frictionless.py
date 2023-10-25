from __future__ import annotations

from frictionless import Package, Schema, Field
from frictionless.resources import TableResource
from . import models as m


def to_frictionless_field(field: m.Field[m.FieldType]) -> Field:
    return Field(
        name=field.meta.name,
        description=field.meta.description,
        title=field.meta.title,
        missing_values=list(field.type.missingValues or []),
    )


def to_frictionless_schema(schema: m.TableSchema) -> Schema:
    return Schema(
        fields=[to_frictionless_field(f) for f in schema.fields],
        missing_values=list(schema.missingValues or []),
    )


def to_frictionless_tableresource(table: m.TableResource) -> TableResource:
    return TableResource(
        name=table.name,
        description=table.description,
        format="inline",
        schema=to_frictionless_schema(table.schema),
        data=list(table.data),
        profile="tabular-data-resource",
    )


def to_frictionless_package(package: m.Package) -> Package:
    return Package(
        name=package.name,
        description=package.description,
        resources=[to_frictionless_tableresource(r) for r in package.resources]
    )
