def nested_stays_dict(data):
    d = Diot(data, convert_nested_dicts=False)
    return d['x']