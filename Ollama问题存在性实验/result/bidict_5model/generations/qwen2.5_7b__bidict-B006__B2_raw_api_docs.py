def set_through_inverse(pairs, key, val):
    b = bidict()
    try:
        b.inv[val] = key
    except ValueDuplicationError:
        raise  # Re-raise if there is an issue with the value duplication
    return b[key]