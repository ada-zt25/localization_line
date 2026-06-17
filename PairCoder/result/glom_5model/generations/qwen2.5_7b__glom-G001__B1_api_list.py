def deep_get(data, path):
    try:
        return glom(data, path)
    except PathAccessError:
        return None