def make_frozen(pairs):
  b = bidict()
  try:
    b.putall(pairs)
  except DuplicationError as e:
    raise ValueError(f"Conflicting pairs in input: {e}") from e
  return frozenbidict(b)