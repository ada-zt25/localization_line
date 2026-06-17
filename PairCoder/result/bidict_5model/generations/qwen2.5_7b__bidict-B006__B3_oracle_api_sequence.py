from bidict import bidict

def set_through_inverse(pairs, key, val):
    b = bidict(pairs)
    try:
        b.inverse[val] = key
    except ValueDuplicationError as e:
        raise DuplicationError from e
    return b[key]