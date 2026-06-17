def reject_dup(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except ValueDuplicationError:
        pass
    return dict(b.inv)