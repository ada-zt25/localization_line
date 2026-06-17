def roundtrip(pairs, key):
  b = OrderedBidict()
  for k, v in pairs:
    b[k] = v
  return b.inv[b[key]]