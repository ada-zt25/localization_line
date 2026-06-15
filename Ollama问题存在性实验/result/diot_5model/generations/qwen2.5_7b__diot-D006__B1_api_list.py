def nested_is_diot(data):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    if isinstance(d.x, Diot):
        return d.x
    else:
        raise DiotFrozenError("Nested data is not a Diot instance")