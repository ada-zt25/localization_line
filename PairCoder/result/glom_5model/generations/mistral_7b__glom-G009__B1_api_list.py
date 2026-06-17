from typing import Any, List, Dict
import glom

def first_item(data: Any) -> List[Any]:
    return Coalesce(*[glom(data, spec) for spec in [('items', ['v'])]])