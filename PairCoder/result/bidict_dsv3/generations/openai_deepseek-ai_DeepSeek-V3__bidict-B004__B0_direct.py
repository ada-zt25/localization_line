def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.put(key, val)
    except ValueDuplicationError:
        old_key = b.inverse[val]
        del b[old_key]
        b[key] = val
    return dict(b)