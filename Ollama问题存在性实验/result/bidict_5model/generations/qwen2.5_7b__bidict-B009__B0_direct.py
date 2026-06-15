def make_frozen(pairs):
    try:
        return frozenbidict(pairs)
    except DuplicationError as e:
        raise ValueError("Duplicate keys or values in pairs") from e