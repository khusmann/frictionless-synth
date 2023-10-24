# import typing as t
from . import generators as gen
from . import config as cfg
# from . import models as m

rnd_state = gen.RandState()


def cli():
    # print(gen.batch(gen.enum_string_field_type(), 200)(rnd_state))
    print(cfg.Word())
    g = (cfg.parse_gencfg(
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
                {"type": "field_group"},
                {
                    "type": "interval",
                    "start_min": -10, "start_max": 10, "length_min": 1, "length_max": 10,
            },
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
