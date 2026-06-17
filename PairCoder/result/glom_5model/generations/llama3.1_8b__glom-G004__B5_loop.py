def restructure(data):
    name = glom(data, 'a.b', default='')
    n = len(glom(data, 'items', default=[]))
    return {'name': name, 'n': n}