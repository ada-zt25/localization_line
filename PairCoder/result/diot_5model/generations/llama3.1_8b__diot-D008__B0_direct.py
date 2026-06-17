def todict_then_index(data):
    diot = Diot.from_dict(data)
    plain_dict = diot.to_plain_dict()
    return plain_dict['x']['y']