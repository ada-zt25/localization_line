def assign_in_place(data, path, val):
    spec = Coalesce(Assign(path, T), Path(path))
    result = glom(data, spec)
    return result