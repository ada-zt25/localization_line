def set_through_inverse(pairs, key, val):
    b = OrderedBidict(pairs)
    b.inverse[val] = key
    return b[key]