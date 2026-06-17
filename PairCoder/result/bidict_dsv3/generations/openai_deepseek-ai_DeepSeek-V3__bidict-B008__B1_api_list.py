def atomic_add(pairs, batch):
    try:
        b = bidict(pairs)
        b.putall(batch)
        return dict(b)
    except DuplicationError:
        return dict(pairs)