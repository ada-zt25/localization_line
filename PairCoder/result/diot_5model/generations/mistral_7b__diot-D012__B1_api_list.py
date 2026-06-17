def thaw_is_temporary(data, key, val):
    diot = Diot(data)
    with diot.frozen() as f_diot:
        if isinstance(f_diot, FrozenDiot):
            f_diot[key] = val
            return FrozenDiot(f_diot.to_dict())
        else:
            raise ValueError("Input diot is not frozen.")