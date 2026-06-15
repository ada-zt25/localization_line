def make_frozen(pairs):
    try:
        return frozenbidict(pairs)
    except DuplicationError as e:
        raise ValueError("Duplicate key or value in pairs") from e