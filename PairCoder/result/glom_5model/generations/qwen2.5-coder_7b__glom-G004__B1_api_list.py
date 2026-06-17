def restructure(data):
    return {
        'name': glom(data, ('a.b', Coalesce(str))),
        'n': len(glom(data, 'items', default=[]))
    }