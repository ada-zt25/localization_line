def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        old_key = next(k for k, v in pairs if v == val)
        b.forceput(key, val)
    except StopIteration:  # val not found in original mapping
        b[key] = val
    return dict(b)