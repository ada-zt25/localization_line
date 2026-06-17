def assign_in_place(data, path, val):
    data = glom(data, Assign(path, T(val)))
    return Coalesce(*[data[path] for path in Path.split(path)])