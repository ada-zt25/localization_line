def inverse_view(pairs):
    try:
        bidict_obj = bidict(pairs)
        return bidict_obj.inv
    except DuplicationError as e:
        raise ValueError("Pairs contain duplicate keys or values") from e