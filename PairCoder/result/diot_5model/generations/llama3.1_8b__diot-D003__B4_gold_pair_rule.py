def get_default(data, key):
    try:
        with FrozenDiot(data).thaw() as d:
            return d.get(key, 0)
    except DiotFrozenError:
        pass
    return data.get(key, 0)