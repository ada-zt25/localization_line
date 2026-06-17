def safe_get(data, path):
  try:
    return glom(data, T[Path(path)])
  except PathAccessError:
    return -1