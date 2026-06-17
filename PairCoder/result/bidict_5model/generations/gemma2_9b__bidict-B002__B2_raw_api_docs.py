def invert(pairs):
  b = OrderedBidict()
  for k, v in pairs.items():
    b.forceput(k, v)
  return dict(b.inv)