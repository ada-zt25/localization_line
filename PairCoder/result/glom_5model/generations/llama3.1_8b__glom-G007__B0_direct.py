def assign_in_place(data, path, val):
    glom.assign(data, Path(path), Coalesce(Assign(val)))
    return glom.glom(data, Path(path))