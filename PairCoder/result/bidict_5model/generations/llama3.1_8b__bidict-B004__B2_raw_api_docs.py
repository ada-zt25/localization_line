def remap(pairs, key, val):
    b = pairs.inv.forceput(val)
    return dict(b)