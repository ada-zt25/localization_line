def atomic_add(pairs, batch):
    b = bidict(pairs)
    try:
        b.putall(batch)
    except DuplicationError:
        pass
    return dict(b)