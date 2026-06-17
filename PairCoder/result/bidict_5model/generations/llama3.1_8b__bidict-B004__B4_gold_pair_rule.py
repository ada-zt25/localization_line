def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except DuplicationError as e:
        if isinstance(e, ValueDuplicationError) and not isinstance(e, KeyDuplicationError):
            raise
    return dict(b)