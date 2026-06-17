def reject_dup(pairs, key, val):
  b = bidict(pairs)
  try:
    b.forceput(key, val)
  except DuplicationError:
    return dict(b) 
  return dict(b)