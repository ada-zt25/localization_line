def to_plain_dict(data):
    if isinstance(data, Diot):
        with data.thaw() as d:
            return d.to_dict()
    return data