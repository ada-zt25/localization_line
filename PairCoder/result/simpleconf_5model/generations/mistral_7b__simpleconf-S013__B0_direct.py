from contextlib import contextmanager
import simpleconf

def use_then_with_restore(profiles):
    with profiles['default'].with_profile('prod'):
        mid = profiles['default'].conf.x

    with profiles['default'].with_profile('default'):
        after = profiles['default'].conf.x

    profiles['default'].switch_to('prod')
    return (mid, after)