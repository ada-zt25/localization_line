def assign_in_place(data, path, val):
    assign_spec = Assign(T[path], val)
    glom(data, assign_spec)
    return glom(data, Path(path))