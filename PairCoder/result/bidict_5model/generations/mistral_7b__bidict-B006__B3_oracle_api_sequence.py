from bidict import bidict, frozenbidict, OrderedBidict

def set_through_inverse(pairs, key, val):
    b = OrderedBidict(frozenbidict(pairs))
    try:
        b.inverse[val] = key
    except DuplicationError as e:
        raise ValueError("KeyDuplicationError occurred while setting through inverse") from e
    return b[key]