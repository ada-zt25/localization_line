from bidict import Bidict, frozenbidict

def atomic_add(pairs, batch):
    b = pairs.copy()
    for key, value in batch:
        try:
            b[key] = value
        except DuplicationError:
            return dict(b)
    return dict(b)