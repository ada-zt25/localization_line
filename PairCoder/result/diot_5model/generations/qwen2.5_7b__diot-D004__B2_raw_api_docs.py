def to_plain_dict(data):
    if isinstance(data, Diot) or isinstance(data, FrozenDiot):
        diot = data.transform('safe').nest(False)
        return diot.to_dict()
    elif isinstance(data, dict):
        return {k: to_plain_dict(v) for k, v in data.items()}
    else:
        return data