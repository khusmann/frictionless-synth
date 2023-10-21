from . import generators as gen

rnd_state = gen.RandState()


def cli():
    # print(gen.batch(gen.enum_string_field_type(), 200)(rnd_state))
    print(gen.assorted_measure()(rnd_state))
