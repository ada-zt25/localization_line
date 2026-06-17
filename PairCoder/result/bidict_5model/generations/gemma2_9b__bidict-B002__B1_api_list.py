def invert(pairs):
  b = OrderedBidict()
  b.putall(pairs)
  return dict(b.inv)