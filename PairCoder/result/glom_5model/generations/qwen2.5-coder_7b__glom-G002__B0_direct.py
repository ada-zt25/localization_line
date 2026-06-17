def apply_after_nav(data):
    return glom(data, T.nums | Coalesce(0) | sum)