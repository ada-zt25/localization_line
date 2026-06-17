def reject_dup(pairs, key, val):
    b = bidict(pairs)
    try:
        b[key] = val
    except DuplicationError:
        pass
    return dict(b)