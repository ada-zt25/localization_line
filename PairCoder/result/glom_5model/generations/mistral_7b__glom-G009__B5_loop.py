def first_item(data):
    return Coalesce(glom(data, 'items[0].v'), [])[0]