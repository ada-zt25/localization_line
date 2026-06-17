from typing import Any, Union
import glom

def apply_after_nav(data: Any) -> Union[int, float]:
    return glom.Coalesce(glom.Sum(Path('nums', data)))