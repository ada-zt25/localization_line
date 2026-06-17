def add_then_lookup(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except DuplicationError:
        pass  # ignore if key or value already exists
    return b.inv[val]