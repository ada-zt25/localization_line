def restructure(data):
    name = glom(data, 'a.b', default=None)
    n = glom(data, 'items', default=[]).__len__()
    return {'name': name, 'n': n}