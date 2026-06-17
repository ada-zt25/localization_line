from bidict import bidict, frozenbidict, OrderedBidict

def roundtrip(pairs, key):
    b = bidict(frozenbidict(pairs))
    return b.inv[b[key]]