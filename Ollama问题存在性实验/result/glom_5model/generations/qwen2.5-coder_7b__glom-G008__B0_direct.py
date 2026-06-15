def assign_return_target(data, path, val):
    glom.assign(data, path, val, missing=glom.Coalesce(None))
    return data