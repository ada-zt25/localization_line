def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        old_key = next(k for k, v in pairs.items() if v == val)
        b.forceput(key, val)
    except StopIteration:
        raise ValueError(f"No existing key found for value {val}")
    return dict(b)