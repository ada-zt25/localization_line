def roundtrip(pairs, key):
    b = OrderedBidict()
    b.putall(pairs)
    value = b[key]
    recovered_key = b.inv[value]
    return recovered_key