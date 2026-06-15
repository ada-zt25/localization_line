def get_default(data, key):
    try:
        return Diot(data)[key]
    except KeyError:
        return 0