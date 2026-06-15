def todict_then_index(data):
    d = Diot(data, diot_nest=False)
    plain_dict = d.to_dict()
    return plain_dict['x']['y']