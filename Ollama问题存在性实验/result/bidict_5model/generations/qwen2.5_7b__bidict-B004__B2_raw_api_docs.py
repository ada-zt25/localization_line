def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except ValueDuplicationError as e:
        old_key = e.key
        del b[old_key]
        b[key] = val
    return dict(b)