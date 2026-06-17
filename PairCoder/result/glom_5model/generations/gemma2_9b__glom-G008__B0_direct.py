def assign_return_target(data, path, val):
  return Assign(glom.PathAccess(data, path), val).apply(data)