def make_frozen(pairs):
    b = bidict(pairs)
    return frozenbidict(b)