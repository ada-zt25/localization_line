def deep_get(data, path):
    return glom(data, T(path))