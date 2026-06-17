def roundtrip(pairs, key):
    from bidict import bidict
    
    b = bidict(pairs)
    try:
        value = b[key]
        return b.inv[value]
    except (KeyDuplicationError, ValueDuplicationError, DuplicationError) as e:
        raise ValueError("Duplicate keys or values found in the bidirectional mapping") from e