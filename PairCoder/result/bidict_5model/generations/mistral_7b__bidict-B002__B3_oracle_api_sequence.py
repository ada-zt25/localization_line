from bidict import bidict, frozenbidict, OrderedBidict

def invert(pairs):
    b = bidict(pairs)
    return dict(b.inverse)