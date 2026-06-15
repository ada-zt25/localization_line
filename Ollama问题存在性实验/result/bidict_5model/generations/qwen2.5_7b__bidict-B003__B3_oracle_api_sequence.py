def inverse_view(pairs):
    try:
        b = bidict(pairs)
        return b.inv
    except DuplicationError as e:
        raise ValueError("Pairs contain duplicate keys or values") from e