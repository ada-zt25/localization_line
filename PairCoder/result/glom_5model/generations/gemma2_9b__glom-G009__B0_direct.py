def first_item(data):
  return Coalesce(T[Path('items', 0, 'v')](data))