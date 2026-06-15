def invert(pairs):
    bidict_instance = bidict(pairs)
    inverse_mapping = dict(bidict_instance.inverse)
    return inverse_mapping