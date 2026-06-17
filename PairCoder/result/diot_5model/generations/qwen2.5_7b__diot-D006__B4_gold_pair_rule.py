def nested_is_diot(data):
    d = Diot(data, diot_nest=True)
    return d.x.to_dict() if isinstance(d.x, Diot) else None