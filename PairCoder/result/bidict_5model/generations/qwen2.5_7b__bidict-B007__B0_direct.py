def roundtrip(pairs, key):
    from bidict import bidict
    
    try:
        b = bidict(pairs)
        value = b[key]
        recovered_key = b.inv[value]
        return recovered_key
    except (KeyDuplicationError, ValueDuplicationError, DuplicationError) as e:
        raise e