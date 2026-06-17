def summarize(data):
    return glom(data, ('nums', {'total': sum, 'count': len}))