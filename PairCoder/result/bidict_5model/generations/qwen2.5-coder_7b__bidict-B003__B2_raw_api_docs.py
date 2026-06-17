def inverse_view(pairs):
    b = OrderedBidict()
    try:
        b.putall(pairs)
    except DuplicationError as e:
        raise ValueError("Duplicate keys or values in pairs") from e
    return b.inv