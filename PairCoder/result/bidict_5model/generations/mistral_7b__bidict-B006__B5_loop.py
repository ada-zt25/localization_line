def set_through_inverse(pairs, key, val):
    b = bidict(pairs)
    try:
        b.inv[val] = key
    except DuplicationError as e:
        raise ValueError("Key duplication error occurred") from e
    return b[key]