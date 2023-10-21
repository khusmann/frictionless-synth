from .frictionless import FieldInfoFactory


def cli():
    print(FieldInfoFactory.build().model_dump_json())
