def atomic_add(pairs, batch):
    try:
        temp_dict = pairs.copy()
        for key, value in batch:
            if key in temp_dict or value in temp_dict.values():
                raise DuplicationError
            temp_dict[key] = value
        return dict(temp_dict)
    except DuplicationError:
        return dict(pairs)