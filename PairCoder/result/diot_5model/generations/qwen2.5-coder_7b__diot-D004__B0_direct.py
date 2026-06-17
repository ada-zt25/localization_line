def to_plain_dict(data):
    if isinstance(data, Diot) or isinstance(data, OrderedDiot) or isinstance(data, FrozenDiot):
        return {k: to_plain_dict(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [to_plain_dict(item) for item in data]
    else:
        return data