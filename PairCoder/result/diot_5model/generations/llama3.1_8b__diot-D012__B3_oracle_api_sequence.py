def thaw_is_temporary(data, key, val):
    d = FrozenDiot(data)
    with d.thaw() as diot:
        diot[key] = val
    return d.freeze()