# import typing as t
from . import generators as gen
from . import config as cfg
from . import frictionless as fric

rnd_state = gen.RandState()


def cli():
    package = cfg.Package().build()(rnd_state)

    fpackage = fric.to_frictionless_package(package)

    fpackage.to_json("synth_package.json")
