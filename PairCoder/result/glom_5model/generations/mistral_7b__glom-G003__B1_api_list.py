def pluck_list(data):
    return Coalesce(*[glom(data, ['items', i, 'v']) for i in range(len(data['items']))])