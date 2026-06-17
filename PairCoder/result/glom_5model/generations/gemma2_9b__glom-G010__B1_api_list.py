def summarize(data):
  return glom(data, {
    'total': Coalesce(glom('nums', sum), glom('nums', lambda x: 0)),
    'count': glom('nums', len)
  })