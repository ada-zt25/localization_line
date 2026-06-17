def set_then_get(key, val):
    d = Diot(data={}, diot_transform='safe', diot_nest=True, diot_frozen=False)
    with d.thaw():
        d[key] = val
    return d.get(key)