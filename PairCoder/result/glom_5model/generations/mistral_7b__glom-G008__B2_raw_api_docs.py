def assign_return_target(data, path, val):
    return Assign(path, T(val))(data)