from bidict import bidict, frozenbidict

def invert(pairs):
    b = bidict()
    for k, v in pairs.items():
        b.forceput(v, k)
    return dict(b.inv)