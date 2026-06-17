def roundtrip(pairs, key):
    b = bidict()
    try:
        for k, v in pairs:
            b.forceput(k, v)
        value = b[key]
        recovered_key = b.inv[value]
        return recovered_key
    except (ValueDuplicationError, KeyDuplicationError, DuplicationError):
        raise