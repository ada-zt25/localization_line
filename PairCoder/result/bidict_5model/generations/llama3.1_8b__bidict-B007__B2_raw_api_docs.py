from bidict import bidict, inv

def roundtrip(pairs, key):
    b = bidict()
    b.forceput(*pairs)
    value = b[key]
    return b.inv[value]