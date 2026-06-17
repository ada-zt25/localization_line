def restructure(data):
  return glom(data, {
    'name': T['a']['b'],
    'n': Coalesce(Assign(T['items'], len), 0)
  })