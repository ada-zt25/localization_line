def access_snake(data):
  d = OrderedDiot({f'{k.lower().replace(" ", "_")}': v for k, v in data.items()})
  return d.foo_bar