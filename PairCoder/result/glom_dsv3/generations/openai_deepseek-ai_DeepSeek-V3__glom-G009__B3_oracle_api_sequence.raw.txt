def first_item(data):
    return glom(data, ('items', [{'v': 'v'}], Coalesce(T[0]['v'])))