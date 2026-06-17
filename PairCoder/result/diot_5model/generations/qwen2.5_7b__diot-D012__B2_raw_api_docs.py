def thaw_is_temporary(data, key, val):
    fd = FrozenDiot(data)
    with fd.thaw():
        fd[key] = val
    return fd