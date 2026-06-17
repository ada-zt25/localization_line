def add_then_lookup(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except ValueDuplicationError:
        pass  # ignore if value already exists
    return b.inv[val]