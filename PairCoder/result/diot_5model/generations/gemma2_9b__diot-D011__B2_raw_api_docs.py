def thaw_to_modify(data, key, val):
  with FrozenDiot.thaw(FrozenDiot(data)) as d:
    d[key] = val
  return d[key]