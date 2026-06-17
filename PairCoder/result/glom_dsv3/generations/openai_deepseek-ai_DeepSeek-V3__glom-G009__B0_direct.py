def first_item(data):
    return glom(data, ('items', [{'v': 'v'}], 0, 'v'))