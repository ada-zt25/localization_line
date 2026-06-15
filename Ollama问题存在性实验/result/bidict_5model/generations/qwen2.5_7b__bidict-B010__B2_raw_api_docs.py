def reject_dup(pairs, key, val):
    b = bidict()
    try:
        for k, v in pairs:
            b[k] = v
        b[key] = val
    except ValueDuplicationError:
        pass
    
    return dict(b)