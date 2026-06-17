def pluck_list(data):
    return glom.glom(data, 'items.*.v')