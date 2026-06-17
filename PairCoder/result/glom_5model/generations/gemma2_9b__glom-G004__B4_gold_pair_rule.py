def restructure(data):
  return glom(data, {'name': 'a.b', 'n': ('items', len)})