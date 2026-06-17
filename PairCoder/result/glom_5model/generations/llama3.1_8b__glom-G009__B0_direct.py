def first_item(data):
    return glom.glom(data, 'items[0].v')