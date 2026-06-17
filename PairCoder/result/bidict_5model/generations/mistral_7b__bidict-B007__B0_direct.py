from bidict import bidict, frozenbidict, OrderedBidict

def roundtrip(pairs, key):
    bidict_obj = bidict(pairs)
    value = bidict_obj[key]
    return bidict_obj.inv[value]