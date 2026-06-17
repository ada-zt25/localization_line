def add_then_lookup(pairs, key, val):
    b = OrderedBidict()
    try:
        b.putall(pairs)
        b[key] = val
        return b.inv[val]
    except (ValueDuplicationError, KeyDuplicationError) as e:
        raise DuplicationError from e