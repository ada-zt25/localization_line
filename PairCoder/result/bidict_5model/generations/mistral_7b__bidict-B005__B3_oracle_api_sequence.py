from bidict import bidict, frozenbidict, OrderedBidict

def add_then_lookup(pairs, key, val):
    b = bidict(frozenbidict(pairs))
    b[key] = val
    return b.inv[val]