def apply_after_nav(data):
    return glom(data, Coalesce(Assign(T(), 0), Path('nums')), default=0)