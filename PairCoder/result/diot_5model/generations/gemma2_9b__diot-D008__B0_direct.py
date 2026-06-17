def todict_then_index(data):
  di = Diot({'x': {'y': data['x']['y']}})
  return dict(di)['x']['y']