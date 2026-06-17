def invert(pairs):
  return OrderedBidict.fromkeys(pairs.values(), pairs.keys()).inverse()