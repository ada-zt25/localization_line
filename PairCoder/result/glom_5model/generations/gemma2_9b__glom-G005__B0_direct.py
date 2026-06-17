def safe_get(data, path):
  try:
    return glom(data)(Path(path))
  except PathAccessError:
    return -1