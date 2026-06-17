def assign_return_target(data, path, val):
    Assign_(val, Path(path))(glom(data))
    return glom.data