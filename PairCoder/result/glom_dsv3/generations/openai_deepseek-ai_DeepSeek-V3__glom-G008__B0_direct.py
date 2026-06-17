def assign_return_target(data, path, val):
    Assign(path, val).glom(data)
    return data