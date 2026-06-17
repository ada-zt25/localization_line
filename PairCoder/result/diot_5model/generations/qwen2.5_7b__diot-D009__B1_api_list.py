def set_then_get(key, val):
    d = Diot(diot_frozen=False)
    with d.thaw():
        d[key] = val
    return d[key]