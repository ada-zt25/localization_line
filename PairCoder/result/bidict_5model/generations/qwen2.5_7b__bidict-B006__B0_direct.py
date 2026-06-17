from bidict import bidict

def set_through_inverse(pairs, key, val):
    b = bidict(pairs)
    try:
        b.inverse[val] = key
    except KeyError:
        raise ValueError("Value does not exist in the bidirectional dictionary")
    return b[key]