import typing as t
from . import generators as gen
from . import config as cfg

rnd_state = gen.RandState()


def cli():
    # print(gen.batch(gen.enum_string_field_type(), 200)(rnd_state))
    print(gen.package()(rnd_state))
    print(cfg.Word())
    g = (cfg.Maybe[t.Optional[int]].model_validate(
        {
            "type": "maybe",
            "child": {
                "type": "maybe",
                "child": {
                    "type": "integer",
                },
            },
        }
    ))
    print(g)
    print(g.model_dump_json())
    print(g.build()(rnd_state))
#    print(cfg.Boop.model_validate(
#        {
#            "z": {
#                "type": "word"
#            }
#        }
#    ))
