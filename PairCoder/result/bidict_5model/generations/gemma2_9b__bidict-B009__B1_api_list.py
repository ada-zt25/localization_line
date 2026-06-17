def make_frozen(pairs):
  b = bidict()
  try:
    b.putall(pairs)
  except DuplicationError as e:
    raise ValueError(f"Cannot create immutable bidict: {e}") from e
  return frozenbidict(b)