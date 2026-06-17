from bidict import bidict

def key_for(pairs, val):
    b = bidict(pairs)
    return b.inv[val]