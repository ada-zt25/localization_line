def thaw_is_temporary(data, key, val):
    with FrozenDiot(data, diot_frozen=True) as d:
        d[key] = val
    return d