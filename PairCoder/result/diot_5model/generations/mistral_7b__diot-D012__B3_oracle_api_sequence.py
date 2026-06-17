def thaw_is_temporary(data, key, val):
    frozen_diot = FrozenDiot(data)
    with frozen_diot.thaw() as d:
        d[key] = val
    return frozen_diot.freeze()