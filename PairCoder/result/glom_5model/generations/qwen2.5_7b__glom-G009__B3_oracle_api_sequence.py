def first_item(data):
    return glom(data, T['items'][0]['v'], default=None, when=PathAccessError, otherwise=T)