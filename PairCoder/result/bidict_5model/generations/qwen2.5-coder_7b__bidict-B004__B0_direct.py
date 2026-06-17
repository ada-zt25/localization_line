def remap(pairs, key, val):
    bd = OrderedBidict(pairs)
    try:
        old_key = bd.inverse[val]
        del bd[old_key]
    except KeyError:
        pass
    bd[key] = val
    return dict(bd)