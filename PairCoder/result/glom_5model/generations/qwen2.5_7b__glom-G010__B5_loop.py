def summarize(data):
    total = glom(data, ('nums', sum), default=0)
    count = glom(data, ('nums', len), default=0)
    return {'total': total, 'count': count}