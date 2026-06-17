import glom

def deep_get(data, path):
    return glom.glom(data, path, default=None)