def assign_return_target(data, path, val):
    try:
        glom(data, Assign(path, val))
        return data
    except PathAccessError:
        pass

    spec = Coalesce(Path(path), [])
    target = glom(data, spec)
    if not isinstance(target, list):
        raise ValueError("The path provided does not point to a list.")

    if len(target) == 1:
        target[0] = val
        return data

    raise ValueError("The specified path points to a list with more than one element.")