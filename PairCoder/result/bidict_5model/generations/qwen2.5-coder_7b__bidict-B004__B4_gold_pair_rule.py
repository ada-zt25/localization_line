def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except DuplicationError:
        pass
    return dict(b)