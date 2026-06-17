def make_frozen(pairs):
    b = bidict()
    b.putall(pairs)
    return frozenbidict(b)