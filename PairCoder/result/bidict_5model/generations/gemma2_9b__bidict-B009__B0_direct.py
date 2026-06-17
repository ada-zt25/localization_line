def make_frozen(pairs):
  result = OrderedBidict()
  for k, v in pairs:
    result[k] = v
  return frozenbidict(result)