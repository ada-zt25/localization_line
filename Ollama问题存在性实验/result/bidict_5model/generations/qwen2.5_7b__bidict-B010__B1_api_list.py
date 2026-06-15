def reject_dup(pairs, key, val):
    b = bidict(pairs)
    try:
        b[key] = val
    except ValueDuplicationError:
        return dict(b)
    else:
        raise Exception("No value duplication error occurred, expected failure")