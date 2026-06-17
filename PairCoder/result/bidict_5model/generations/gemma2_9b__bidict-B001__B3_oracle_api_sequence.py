def key_for(pairs, val):
  b = bidict(pairs)
  return b.inverse[val]