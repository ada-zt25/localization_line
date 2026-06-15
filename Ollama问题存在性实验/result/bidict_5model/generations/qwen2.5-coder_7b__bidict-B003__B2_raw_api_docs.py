def inverse_view(pairs):
    b = bidict()
    try:
        b.putall(pairs)
    except DuplicationError:
        raise ValueError("Pairs contain duplicate keys or values")
    return b.inv