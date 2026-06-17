def assign_return_target(data, path, val):
    try:
        glom(data, Assign(path, val))
        return data
    except PathAccessError:
        pass

    spec = Coalesce(Path(path), [])
    result = glom(data, spec)
    if not isinstance(result, list):
        result = [result]
    for i, item in enumerate(result):
        try:
            glom(data[i], Assign(path[i], val))
            return data
        except PathAccessError:
            pass

    raise ValueError(f"Path '{path}' not found in the given data.")