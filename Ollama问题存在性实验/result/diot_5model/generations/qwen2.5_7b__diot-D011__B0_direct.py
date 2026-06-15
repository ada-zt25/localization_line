def thaw_to_modify(data, key, val):
    from diot import FrozenDiot, thaw
    
    fd = FrozenDiot(data)
    with thaw(fd) as d:
        d[key] = val
    return d[key]