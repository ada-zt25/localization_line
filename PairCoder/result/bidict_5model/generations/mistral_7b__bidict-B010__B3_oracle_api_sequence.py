from bidict import bidict, frozenbidict, OrderedBidict

def reject_dup(pairs, key, val):
    b = bidict(pairs)
    try:
        b[key] = val
    except ValueDuplicationError as e:
        pass
    return dict(b)