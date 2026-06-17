def apply_after_nav(data):
    return Coalesce(glom(data, 'nums', default=[]), glom(Coalesce(*[glom(x, {'sum': T.sum}) for x in data['nums']]))