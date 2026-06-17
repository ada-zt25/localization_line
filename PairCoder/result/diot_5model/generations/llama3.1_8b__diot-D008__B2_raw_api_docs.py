def todict_then_index(data):
    diot = Diot(data, diot_nest=False)
    plain_dict = diot.to_dict()
    return plain_dict['x']['y']