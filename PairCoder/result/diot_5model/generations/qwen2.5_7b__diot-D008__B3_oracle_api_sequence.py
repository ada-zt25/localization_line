def todict_then_index(data):
    d = Diot(data)
    plain_dict = d.toatoms()
    result = plain_dict['x']['y']
    return result