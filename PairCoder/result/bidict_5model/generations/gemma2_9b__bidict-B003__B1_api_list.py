def inverse_view(pairs):
  b = bidict()
  b.putall(pairs)
  return b.inv