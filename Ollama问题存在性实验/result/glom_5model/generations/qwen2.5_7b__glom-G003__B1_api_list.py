def pluck_list(data):
    return glom(data, Path('items')['v'], default=[])