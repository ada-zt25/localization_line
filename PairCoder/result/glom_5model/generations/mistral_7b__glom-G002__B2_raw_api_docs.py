from glom import Coalesce, T, Path, glom

def apply_after_nav(data):
    return Coalesce(glom(T(data), ('nums', sum)))