def thaw_to_modify(data, key, val):
    d = FrozenDiot(data)
    with d.thaw() as thawed:
        thawed[key] = val
    return d[key]