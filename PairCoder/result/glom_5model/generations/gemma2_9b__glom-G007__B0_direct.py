def assign_in_place(data, path, val):
  return Assign(glom.Coalesce(T(data), Path(path)), val).apply(data)