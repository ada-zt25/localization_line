def todict_then_index(data):
    d = Diot(data)
    converted = d.to_dict()
    return converted['x']['y']