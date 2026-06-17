def assign_return_target(data, path, val):
  return glom(data, Assign(path, val))