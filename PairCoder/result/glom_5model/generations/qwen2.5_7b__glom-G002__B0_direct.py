from glom import Coalesce, Assign, T, Path

def apply_after_nav(data):
    return glom(data, Coalesce(Path('nums').sum(), 0))