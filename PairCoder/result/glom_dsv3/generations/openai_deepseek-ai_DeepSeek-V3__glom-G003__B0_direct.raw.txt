def pluck_list(data):
    return glom(data, ('items', [glom.T['v']]))