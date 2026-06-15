def restructure(data):
    return glom(data, {'name': T['a']['b'], 'n': (Coalesce(T['items'], []) | len)})