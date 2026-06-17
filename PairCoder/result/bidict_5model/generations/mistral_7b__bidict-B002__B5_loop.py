from bidict import bidict, frozenbidict

def invert(pairs):
    b = bidict(pairs)
    return dict(b.inv)