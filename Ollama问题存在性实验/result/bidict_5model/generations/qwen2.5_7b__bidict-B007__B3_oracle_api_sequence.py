def roundtrip(pairs, key):
    from bidict import bidict

    b = bidict(pairs)
    return b.inv[b[key]]