def restructure(data):
    return {'name': Coalesce('a.b', '', data['a']['b']), 'n': len(data['items'])}