def thaw_to_modify(data, key, val):
    d = FrozenDiot(data)
    with d.thaw() as d_thawed:
        d_thawed[key] = val
    return d[key]