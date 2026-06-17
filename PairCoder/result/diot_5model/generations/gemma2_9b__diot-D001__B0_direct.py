def access_camel(data):
  d = OrderedDiot({k.replace('_', ' ').title().replace(' ', ''): v for k, v in data.items()})
  return d.fooBar