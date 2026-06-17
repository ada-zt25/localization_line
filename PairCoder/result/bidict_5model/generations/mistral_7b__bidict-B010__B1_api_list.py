def reject_dup(pairs, key, val):
    b = bidict()
    b.putall(pairs)
    try:
        b.forceput(key, val)
    except DuplicationError as e:
        pass
    return dict(b)