def atomic_add(pairs, batch):
    b = bidict(pairs)
    try:
        for key, value in batch:
            b[key] = value
    except (ValueDuplicationError, KeyDuplicationError, DuplicationError):
        pass
    return dict(b)