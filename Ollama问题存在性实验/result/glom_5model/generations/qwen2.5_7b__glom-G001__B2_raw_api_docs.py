def deep_get(data, path):
    try:
        return glom(data, Path(path))
    except PathAccessError:
        return Coalesce(*[glom(data, Path(p)) for p in path.split('.') if p], default=None)