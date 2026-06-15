def summarize(data):
    return glom(data, {'total': (T['nums'], sum), 'count': (T['nums'], len)})