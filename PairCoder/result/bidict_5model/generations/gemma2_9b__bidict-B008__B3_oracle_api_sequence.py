def atomic_add(pairs, batch):
  try:
    b = OrderedBidict(pairs)
    for key, value in batch:
      b[key] = value
    return dict(b)
  except (KeyDuplicationError, ValueDuplicationError) as e:
    return dict(OrderedBidict(pairs))