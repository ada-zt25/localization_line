def nested_is_diot(data):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    while isinstance(d.x, OrderedDiot) or isinstance(d.x, FrozenDiot):
        d = d.x
    return d if isinstance(d, Diot) else None