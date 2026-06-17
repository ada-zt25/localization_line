def get_default(data, key):
    d = Diot(data)
    return d.get(key, 0)