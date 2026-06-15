def apply_after_nav(data):
    return glom(data, ('nums', Coalesce(sum, 0)))