def deep_get(data, path):
    try:
        return glom.glom(data, path)
    except PathAccessError:
        return None