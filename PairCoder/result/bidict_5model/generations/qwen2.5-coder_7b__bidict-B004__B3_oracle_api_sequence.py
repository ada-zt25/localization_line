def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b[key] = val
    except ValueDuplicationError as e:
        del b[e.existing_key]
        b[key] = val
    return dict(b)