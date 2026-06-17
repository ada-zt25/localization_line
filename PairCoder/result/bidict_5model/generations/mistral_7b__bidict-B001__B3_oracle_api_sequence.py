from bidict import bidict, frozenbidict, OrderedBidict

def key_for(pairs: dict):
    def _key_for(b, val):
        try:
            return next(k for k in b if b[k] == val)
        except StopIteration:
            raise KeyError(f"{val} not found in bidict")

    return lambda: _key_for(bidict(pairs), val)