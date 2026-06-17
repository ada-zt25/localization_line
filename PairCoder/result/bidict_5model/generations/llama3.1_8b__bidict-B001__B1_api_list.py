from bidict import bidict, frozenbidict

def key_for(pairs, val):
    b = bidict(pairs)
    return b.inv[val]