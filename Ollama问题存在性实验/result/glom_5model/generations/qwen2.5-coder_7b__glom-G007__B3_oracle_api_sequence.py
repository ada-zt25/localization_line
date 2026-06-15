def assign_in_place(data, path, val):
    return glom(data, Assign(path, val)) or glom(data, path)