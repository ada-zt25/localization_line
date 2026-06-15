def add_then_lookup(pairs, key, val):
    b = bidict()
    try:
        for k, v in pairs:
            b.putall([(k, v)])
        b.forceput(key, val)
        return b.inv[val]
    except (ValueDuplicationError, DuplicationError):
        return None