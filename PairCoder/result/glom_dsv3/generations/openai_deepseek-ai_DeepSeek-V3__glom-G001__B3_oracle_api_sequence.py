def deep_get(data, path):
    return glom(data, Coalesce(Path(*path.split('.')), default=None))