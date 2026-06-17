def mutate_then_read(data, key, val):
  with ProfileConfig.with_profile(data, 'default'):
    data[key] = val
  return data[key]