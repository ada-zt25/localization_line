def key_for(pairs, val):
    b = OrderedBidict()
    try:
        b.putall(pairs)
        return b.inv[val]
    except DuplicationError as e:
        raise KeyError(f"Value {val} is not unique in the input pairs") from e