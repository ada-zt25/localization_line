from bidict import bidict

def key_for(pairs, val):
    bdict = bidict(pairs)
    try:
        return bdict.inv[val]
    except KeyError:
        raise ValueDuplicationError(f"No unique key found for value {val}")