from bidict import bidict

def add_then_lookup(pairs, key, val):
    b = bidict(pairs)
    b[key] = val
    return b.inv[val]