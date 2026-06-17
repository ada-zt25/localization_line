def add_then_lookup(pairs, key, val):
  b = bidict()
  b[key] = val
  return b.inv[val]