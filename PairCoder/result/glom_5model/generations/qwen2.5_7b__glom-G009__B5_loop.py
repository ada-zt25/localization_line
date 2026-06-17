def first_item(data):
    try:
        return glom(data, 'items.0.v')
    except PathAccessError:
        return None