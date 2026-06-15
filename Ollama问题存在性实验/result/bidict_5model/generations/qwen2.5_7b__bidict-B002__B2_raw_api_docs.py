def invert(pairs):
    b = bidict()
    try:
        for key, value in pairs.items():
            b[key] = value
    except ValueDuplicationError:
        return {}
    return dict(b.inv)