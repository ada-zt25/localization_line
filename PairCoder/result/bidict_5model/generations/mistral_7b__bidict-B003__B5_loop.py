def inverse_view(pairs):
    b = bidict.from_iteritems(pairs)
    return b.inv