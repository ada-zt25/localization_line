def todict_then_index(data):
    diot_obj = Diot(data, diot_nest=False)
    plain_dict = diot_obj.to_dict()
    return plain_dict['x']['y']