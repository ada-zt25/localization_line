def nested_stays_dict(data):
  d = Diot(data, preserve_dicts=True)
  return d['x']