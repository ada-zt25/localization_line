def thaw_is_temporary(data, key, val):
    with FrozenDiot(data).thaw() as d:
        d[key] = val
    return d