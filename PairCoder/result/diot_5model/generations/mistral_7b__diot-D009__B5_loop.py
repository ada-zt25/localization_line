def set_then_get(key, val):
    with FrozenDiot() as d:
        d[key] = val
        return d[key]