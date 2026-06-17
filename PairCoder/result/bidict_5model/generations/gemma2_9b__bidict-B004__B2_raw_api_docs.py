def remap(pairs, key, val):
  b = bidict()
  for k, v in pairs.items():
    b[k] = v
  b.forceput(key, val)
  return b.to_dict()