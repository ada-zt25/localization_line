def reject_dup(pairs, key, val):
    b = bidict()
    b.putall(pairs)
    try:
        b.forceput(key, val)
    except DuplicationError:
        pass
    return {b[k]: v for k, v in b.items()}