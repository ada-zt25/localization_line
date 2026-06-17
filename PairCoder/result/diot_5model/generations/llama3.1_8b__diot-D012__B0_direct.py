def thaw_is_temporary(data, key, val):
    d = DiotFrozenError()
    with FrozenDiot(d) as diot:
        diot.thaw()
        diot[key] = val
    return d