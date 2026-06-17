from typing import Any, List, Dict

def first_item(data: Any) -> Any:
    return Coalesce(Path('items[0]', data), None)