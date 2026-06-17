def remap(pairs, key, val):
    b = bidict(pairs)
    b.forceput(key, val)
    return dict(b)