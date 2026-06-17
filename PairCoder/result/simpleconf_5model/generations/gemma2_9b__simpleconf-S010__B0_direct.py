def mutate_then_read(data, key, val):
  with ProfileConfig() as config:
    config[key] = val
    return config[key]