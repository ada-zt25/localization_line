def reject_dup(pairs, key, val):
    b = bidict(pairs)
    try:
        b.put(key, val)
    except (ValueDuplicationError, DuplicationError):
        pass
    return dict(b)