def thaw_to_modify(data, key, val):
    with data.thaw() as d:
        d[key] = val
    return d[key]