def safe_get(data, path):
    return Coalesce(*[glom(data, spec) for spec in Path(path).split('.' if len(Path(path).split('.')) > 1 else [Path(path)]))