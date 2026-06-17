from bidict import bidict, frozenbidict, OrderedBidict

def invert(pairs):
    bi = OrderedBidict()
    for k, v in pairs.items():
        bi[v] = k
    return dict(bi)