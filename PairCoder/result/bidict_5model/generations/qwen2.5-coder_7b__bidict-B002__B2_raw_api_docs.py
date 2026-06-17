def invert(pairs):
    b = OrderedBidict()
    for key, value in pairs.items():
        try:
            b[key] = value
        except ValueDuplicationError:
            continue
    return dict(b.inv)