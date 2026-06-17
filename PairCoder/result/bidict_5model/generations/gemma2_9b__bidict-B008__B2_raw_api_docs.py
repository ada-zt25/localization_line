def atomic_add(pairs, batch):
  try:
    b = OrderedBidict()
    for k, v in pairs:
      b[k] = v
    b.putall(batch)
    return b.todict()
  except DuplicationError:
    return {}