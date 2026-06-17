def safe_get(data, path):
    try:
        return glom.glom(data, path)
    except PathAccessError:
        return -1