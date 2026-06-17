def thaw_to_modify(data, key, val):
    if not isinstance(data, FrozenDiot):
        raise ValueError("Input data must be a FrozenDiot instance.")

    with data.thaw() as d:
        d[key] = val
        return d[key]