from typing import Dict, Any

def restructure(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'name': Coalesce('a.b', PathAccessError('a', 'b')),
        'n': len(Path('items'))
    }