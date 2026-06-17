def pluck_list(data):
    return Coalesce(*[glom(data, spec) for spec in [['items'], ['items', 0], 'v']])