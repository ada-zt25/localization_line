def assign_in_place(data, path, val):
    spec = Assign(path, val)
    glom(data, spec)
    return glom(data, path)