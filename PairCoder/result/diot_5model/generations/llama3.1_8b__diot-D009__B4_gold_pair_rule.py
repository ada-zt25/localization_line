def set_then_get(key, val):
    d = Diot({'x': {'y': None}})
    with d.thaw():
        d.x.y = val
    return d.x.y