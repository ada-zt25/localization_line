def atomic_add(pairs, batch):
    try:
        temp_dict = bidict(pairs)
        temp_dict.putall(batch)
        return dict(temp_dict)
    except (ValueDuplicationError, KeyDuplicationError, DuplicationError):
        return pairs