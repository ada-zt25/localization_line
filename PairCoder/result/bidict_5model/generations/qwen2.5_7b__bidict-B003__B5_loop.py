def inverse_view(pairs):
    try:
        b = bidict(pairs)
        return b.inv
    except DuplicationError as e:
        raise ValueError("Duplicate key or value in pairs") from e