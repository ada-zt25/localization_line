def safe_get(data, path):
    return Coalesce(*[glom(data, spec) for spec in Path(path).split('.')]) if Path(path) else -1