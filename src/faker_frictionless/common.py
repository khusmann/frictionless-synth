from __future__ import annotations
import typing as t
from faker.providers import address, date_time, python, lorem
from faker import Faker, Generator
from pydantic import BaseModel


class ImmutableBaseModel(BaseModel):
    class Config:
        frozen = True


class SmartFaker(
    date_time.Provider,
    address.Provider,
    python.Provider,
    lorem.Provider,
    Generator,
):
    unique: SmartFaker
    optional: SmartFaker

    def __init__(self):
        msg = "This class is meant to be used only as a type"
        raise RuntimeError(msg)

    @staticmethod
    def create(
        locale: t.Optional[t.Union[str, t.Sequence[str],
                                   t.Dict[str, t.Union[int, float]]]] = None,
        providers: t.Optional[t.List[str]] = None,
        generator: t.Optional[Generator] = None,
        includes: t.Optional[t.List[str]] = None,
        use_weighting: bool = True,
        **config: t.Any,
    ) -> SmartFaker:
        return t.cast(SmartFaker, Faker(
            locale, providers, generator, includes, use_weighting, **config,
        ))


faker = SmartFaker.create()

faker.random_digit()
