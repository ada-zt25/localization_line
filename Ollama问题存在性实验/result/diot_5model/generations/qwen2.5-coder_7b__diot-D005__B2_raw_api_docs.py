def nested_stays_dict(data):
    d = Diot(nest=False)
    d.update(data)
    return d['x']