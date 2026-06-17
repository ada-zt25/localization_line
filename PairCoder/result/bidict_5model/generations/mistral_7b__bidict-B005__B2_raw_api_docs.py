from bidict import bidict, frozenbidict

def add_then_lookup(pairs, key, val):
    bidict_obj = bidict.from_dict(pairs)
    bidict_obj.putall({key: val})
    return bidict_obj.inv[val]