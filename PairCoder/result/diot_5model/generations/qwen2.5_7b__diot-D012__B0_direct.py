def thaw_is_temporary(data, key, val):
    fd = FrozenDiot(data)
    with fd.thaw() as d:
        d[key] = val
    return fd