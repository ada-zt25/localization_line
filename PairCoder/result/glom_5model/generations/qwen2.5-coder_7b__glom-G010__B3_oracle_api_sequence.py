def summarize(data):
    return glom(data, {'total': T.nums | Coalesce(0) | sum, 'count': T.nums | Coalesce([]) | len})