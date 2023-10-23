from . import generators as gen
from . import config as cfg

rnd_state = gen.RandState()


def cli():
    # print(gen.batch(gen.enum_string_field_type(), 200)(rnd_state))
    print(gen.package()(rnd_state))
    print(cfg.Word())
    print(cfg.Maybe[str].model_validate(
        {
            "type": "maybe",
            "gen": {
                "type": "word",
            },
        }
    ))
#    print(cfg.Boop.model_validate(
#        {
#            "z": {
#                "type": "word"
#            }
#        }
#    ))
