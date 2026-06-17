def make_frozen(pairs):
    b = bidict(pairs)
    try:
        b.putall(pairs)
    except DuplicationError:
        pass
    return frozenbidict(b)