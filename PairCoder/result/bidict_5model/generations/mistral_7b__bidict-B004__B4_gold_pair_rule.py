from bidict import bidict, frozenbidict, ValueDuplicationError

def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except ValueDuplicationError:
        pass
    return dict(frozenbidict(b))