def set_through_inverse(pairs, key, val):
    b = bidict(pairs)
    b.forceput(val, key)
    return b[key]