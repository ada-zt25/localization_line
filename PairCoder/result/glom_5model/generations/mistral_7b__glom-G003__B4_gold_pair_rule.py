def pluck_list(data):
    return list(glom(data, ('items', ['v']), default=[]))