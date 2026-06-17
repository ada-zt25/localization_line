def assign_return_target(data, path, val):
    Coalesce(Assign(path, val)(data), data)
    return data