def restructure(data):
    return glom(data, {'name': T['a']['b'], 'n': (T['items'], len)})