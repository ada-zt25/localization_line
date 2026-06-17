def restructure(data):
  return {'name': glom(data, 'a.b', default=''), 'n': len(glom(data, 'items'))}