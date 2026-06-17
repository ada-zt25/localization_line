def thaw_to_modify(data, key, val):
    from diot import FrozenDiot
    
    with FrozenDiot(data).thaw() as d:
        d[key] = val
    return d[key]