def nested_is_diot(data):
    d = Diot(data)
    return getattr(d, 'x')