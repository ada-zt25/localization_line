def restructure(data):
  return {'name': Coalesce(T['a']['b'], ''), 'n': len(data['items'])}