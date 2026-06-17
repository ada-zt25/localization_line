from bidict import bidict, frozenbidict

def key_for(pairs):
    b = bidict()
    b.putall(pairs)
    b_frozen = frozenbidict(b)
    return next(k for k in b if b[k] == pairs[k])