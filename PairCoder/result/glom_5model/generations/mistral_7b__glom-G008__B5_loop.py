def assign_return_target(data, path, val):
    try:
        glom(data, Assign(path, val))
        return data
    except PathAccessError:
        pass

    spec = Coalesce(Path(path), [])
    if not isinstance(spec, list):
        raise ValueError("Invalid path provided")

    for sub_path in spec:
        try:
            glom(data, sub_path, default=[])
            break
        except PathAccessError:
            pass

    if len(spec) > 1:
        for i, sub_path in enumerate(spec[:-1]):
            glom(data[spec[i]], sub_path)
        glom(data[-1], spec[-1])

    data[spec[-1]] = val
    return data