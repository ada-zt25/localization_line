def set_through_inverse(pairs, key, val):
    b = OrderedBidict()
    b.update(pairs)
    try:
        b.inv[val] = key
    except DuplicationError:
        pass
    return b[key]