def remap(pairs, key, val):
  b = bidict(pairs)
  try:
    b[key] = val
  except DuplicationError as e:
    if isinstance(e, ValueDuplicationError):
      b[key] = val
    else:
      raise
  return dict(b)