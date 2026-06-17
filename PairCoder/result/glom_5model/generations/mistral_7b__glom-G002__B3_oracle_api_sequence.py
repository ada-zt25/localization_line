from typing import Any, List

def apply_after_nav(data: Any) -> int:
    return sum(glom(data, 'nums'))