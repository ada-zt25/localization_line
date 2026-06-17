def pluck_list(data):
  return glom(data, Coalesce(T('items'), []), lambda x: x['v'])