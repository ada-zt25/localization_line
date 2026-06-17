from typing import Dict, Any

def restructure(data: Dict[str, Any]) -> Dict[str, Any]:
    name = Coalesce(glom(data, 'a.b'), '')
    n = len(glom(data, 'items'))
    return {'name': name, 'n': n}