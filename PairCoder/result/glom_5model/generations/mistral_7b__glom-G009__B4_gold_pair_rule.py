from typing import Any, List, Dict

def first_item(data: Any) -> List[Any]:
    return Coalesce(*[glom(data, spec) for spec in [('items', 0), ('items.0', 'v')]] if data else [])