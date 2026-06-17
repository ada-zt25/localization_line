def roundtrip(pairs, key):
    b = bidict(pairs)
    return b.inv[b[key]].key