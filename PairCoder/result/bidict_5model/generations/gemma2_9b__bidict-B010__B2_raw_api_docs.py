def reject_dup(pairs, key, val):
  try:
    pairs.forceput(key, val)
  except ValueDuplicationError:
    return dict(pairs)
  return dict(pairs)