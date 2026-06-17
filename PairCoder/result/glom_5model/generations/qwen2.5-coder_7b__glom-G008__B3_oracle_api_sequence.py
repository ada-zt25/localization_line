def assign_return_target(data, path, val):
    spec = Assign(Path(path), Coalesce(val))
    return glom(data, spec)