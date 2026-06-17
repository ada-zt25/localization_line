def roundtrip(pairs, key):
    b = bidict(pairs)
    value = b[key]
    return b.inv[value]