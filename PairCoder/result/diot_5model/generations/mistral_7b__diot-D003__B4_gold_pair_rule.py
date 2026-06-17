def get_default(data, key):
    d = Diot(data)
    try:
        return d[key]
    except KeyError:
        return 0