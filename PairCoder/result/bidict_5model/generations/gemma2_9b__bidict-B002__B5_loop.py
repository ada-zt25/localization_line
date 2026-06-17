def invert(pairs):
  b = bidict()
  b.putall(pairs)
  return dict(b.inv)