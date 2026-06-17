def assign_in_place(data, path, val):
    try:
        glom.assign_in_place(data, T(path), Assign(val))
        return glom.data(data, Path(path))
    except PathAccessError as e:
        raise ValueError(f"Path {path} not found in data") from e