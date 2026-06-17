from typing import Any, List, Dict
import glom

def first_item(data: Any) -> Any:
    return glom.glom(data, 'items[0].v')