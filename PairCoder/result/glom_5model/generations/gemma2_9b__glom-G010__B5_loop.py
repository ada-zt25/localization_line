def summarize(data):
  return glom(data, {'total': Coalesce(sum, .), 'count': len})