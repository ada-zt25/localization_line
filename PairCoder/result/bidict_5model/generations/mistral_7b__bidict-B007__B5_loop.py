from bidict import bidict, frozenbidict, ValueDuplicationError, KeyDuplicationError

def roundtrip(pairs, key):
    b = bidict()
    b.putall(pairs)
    value = b[key]
    return b.inv[value]