def summarize(data):
    return glom(data, {
        'total': ('nums', sum),
        'count': ('nums', len)
    })