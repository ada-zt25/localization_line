def make_frozen(pairs):
    bidict = OrderedBidict()
    for key, value in pairs:
        bidict.forceput(key, value)
    return frozenbidict(bidict)