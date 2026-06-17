def add_then_lookup(pairs, key, val):
    b = OrderedBidict() if not pairs else pairs.copy()
    b.putall({key: val})
    return b.inv[val]