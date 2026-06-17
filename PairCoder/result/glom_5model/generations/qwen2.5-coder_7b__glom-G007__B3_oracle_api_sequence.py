def assign_in_place(data, path, val):
    return glom(data, Assign(Path(path), val))