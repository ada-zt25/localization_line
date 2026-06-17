from contextlib import contextmanager

def use_survives_with(profiles):
    with profiles['prod'].load(), contextmanager(profiles['default'])(None):
        conf = Config()
        return conf.x