def reject_dup(pairs, key, val):
    b = bidict()
    for k, v in pairs.items():
        try:
            b[k] = v
        except ValueDuplicationError:
            pass
    if val in b.inv:
        return dict(b)
    else:
        try:
            b[key] = val
        except ValueDuplicationError:
            pass
        return dict(b)