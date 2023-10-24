import typing as t
from . import generators as gen
from . import config as cfg

rnd_state = gen.RandState()


def cli():
    # print(gen.batch(gen.enum_string_field_type(), 200)(rnd_state))
    print(gen.package()(rnd_state))
    print(cfg.Word())
    g = (cfg.Seq[t.Optional[str] | str].model_validate(
        {
            "type": "seq",
            "children": [{
                "type": "maybe",
                "child": {
                    "type": "unique",
                    "child": {"type": "word"}
                },
                "prob": 0.5,
            },
                {"type": "word"}
            ],
            "size": 20,
            "unique": True,
        }
    ))
    print(g)
    print(g.model_dump_json())
    result = g.build()(rnd_state)
    print(result)
#    print(cfg.Boop.model_validate(
#        {
#            "z": {
#                "type": "word"
#            }
#        }
#    ))
