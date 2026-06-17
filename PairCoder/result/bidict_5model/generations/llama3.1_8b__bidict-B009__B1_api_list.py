from bidict import frozenbidict, putall

def make_frozen(pairs):
    b = bidict(pairs)
    return frozenbidict(b.putall([(v, k) for k, v in b.items()]))