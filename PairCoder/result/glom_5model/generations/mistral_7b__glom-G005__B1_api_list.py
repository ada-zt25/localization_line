from glom import glom, Coalesce, Assign

def safe_get(data, path):
    try:
        return Coalesce(*[glom(data, spec) for spec in Path(path).split('.')] if path else -1
    except PathAccessError:
        return -1