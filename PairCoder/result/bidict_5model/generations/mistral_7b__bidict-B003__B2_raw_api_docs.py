from bidict import bidict, frozenbidict

def inverse_view(pairs):
    bidict_obj = bidict()
    for key, value in pairs:
        bidict_obj.put(value, key)
    return frozenbidict(bidict_obj)