from contextlib import contextmanager

def set_then_get(key, val):
    with Diot({}, diot_frozen=False) as d:
        d[key] = val
        return d[key]