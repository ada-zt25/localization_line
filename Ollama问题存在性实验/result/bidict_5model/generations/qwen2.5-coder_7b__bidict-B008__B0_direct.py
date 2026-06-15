def atomic_add(bidict, batch):
    try:
        for key, value in batch:
            bidict[key] = value
        return dict(bidict)
    except (KeyDuplicationError, ValueDuplicationError) as e:
        return {}