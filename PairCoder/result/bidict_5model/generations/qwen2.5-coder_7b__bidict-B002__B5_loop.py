def invert(pairs):
    b = bidict(pairs)
    return dict(b.inv.items())