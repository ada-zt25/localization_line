def remap(pairs, key, val):
    b = OrderedBidict(pairs)
    b.forceput(key, val)
    return dict(b)