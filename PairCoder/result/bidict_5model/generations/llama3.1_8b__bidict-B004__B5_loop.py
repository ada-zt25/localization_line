def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except KeyDuplicationError:
        pass
    return dict(b)