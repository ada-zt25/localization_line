def apply_after_nav(data):
    return Coalesce(*[glom(data, ('nums', 'sum'))])