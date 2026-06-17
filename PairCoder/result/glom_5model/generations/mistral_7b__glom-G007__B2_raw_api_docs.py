def assign_in_place(data, path, val):
    spec = Coalesce(*Path(path))
    Assign(spec, val)(data)
    return PathAccess(spec)(data)