from typing import Dict, Any
import glom

def restructure(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'name': Coalesce('', glom.Path(['a', 'b'], data)),
        'n': len(glom.Path('items', data))
    }