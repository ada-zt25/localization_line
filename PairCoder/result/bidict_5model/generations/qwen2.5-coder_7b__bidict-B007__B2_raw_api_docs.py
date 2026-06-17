def roundtrip(pairs, key):
    b = OrderedBidict()
    try:
        b.putall(pairs)
        value = b[key]
        recovered_key = b.inv[value]
        return recovered_key
    except (KeyDuplicationError, ValueDuplicationError) as e:
        raise DuplicationError from e