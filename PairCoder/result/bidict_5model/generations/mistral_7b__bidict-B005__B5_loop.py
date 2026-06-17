def add_then_lookup(pairs, key, val):
    b = bidict(pairs)
    b.putall({key: val})
    return b.inv[val]