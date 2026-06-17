def summarize(data):
    return glom.glom(data, ('nums', {'total': 'sum', 'count': 'len'}))