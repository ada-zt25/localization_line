def summarize(data):
    return {'total': Coalesce(glom(data, 'nums', default=0).sum(), 0), 'count': len(Coalesce(glom(data, 'nums'), []))}