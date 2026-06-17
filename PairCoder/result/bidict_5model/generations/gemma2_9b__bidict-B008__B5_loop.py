def atomic_add(pairs, batch):
  try:
    bidict_ = bidict()
    bidict_.putall(pairs)
    bidict_.putall(batch)
    return dict(bidict_)
  except DuplicationError:
    return dict(bidict_)