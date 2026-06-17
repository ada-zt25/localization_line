from bidict import bidict, frozenbidict

def inverse_view(pairs):
    b = bidict()
    for key, value in pairs:
        try:
            b.putall({value: key})
        except DuplicationError:
            pass
    return frozenbidict(b)