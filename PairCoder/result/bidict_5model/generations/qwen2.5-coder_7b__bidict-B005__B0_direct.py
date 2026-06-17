def add_then_lookup(pairs, key, val):
    b = OrderedBidict(pairs)
    b[key] = val
    return b.inv[val]