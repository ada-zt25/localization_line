def merge_three(a, b, c, key):
  Config.load([a, b, c])
  return Config[key]