def summarize(data):
    return glom.glom(data, ('nums', sum), default=0) | {'count': len(glom.glom(data, 'nums'))}