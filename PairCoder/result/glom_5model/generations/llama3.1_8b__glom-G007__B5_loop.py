def assign_in_place(data, path, val):
    glom(target=data, spec=Assign(path, val))
    return glom(target=data, spec=path)