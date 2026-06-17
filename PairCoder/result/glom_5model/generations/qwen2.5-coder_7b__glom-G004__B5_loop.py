def restructure(data):
    return glom(data, {
        'name': ('a.b', str),
        'n': ('items', len)
    })