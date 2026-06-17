def assign_in_place(data, path, val):
    glom(data, Assign(Path(path), val))
    return glom(data, T[path])