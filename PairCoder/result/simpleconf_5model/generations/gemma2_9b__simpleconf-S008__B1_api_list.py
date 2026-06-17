def merge_then_nested(data, k1, k2):
  merged = Config.load(data)
  return merged[k1][k2]