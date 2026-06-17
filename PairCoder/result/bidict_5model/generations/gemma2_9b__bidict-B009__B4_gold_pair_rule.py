def make_frozen(pairs):
  b = bidict()
  try:
    b.putall(pairs)
    return frozenbidict(b)
  except DuplicationError:
    raise