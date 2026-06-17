def atomic_add(pairs, batch):
    temp = bidict(pairs.copy())
    try:
        for key, value in batch:
            temp.put(key, value)
    except (ValueDuplicationError, KeyDuplicationError, DuplicationError):
        return dict(pairs)
    return dict(temp)