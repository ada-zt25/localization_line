def assign_return_target(data, path, val):
    glom(target=data, spec=Assign(path, val))
    return data