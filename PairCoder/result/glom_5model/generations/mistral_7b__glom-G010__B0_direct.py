from typing import Dict, List, Any
import glom

def summarize(data: Dict[str, Any]) -> Dict[str, int]:
    return {
        'total': Coalesce(glom.sum(Path('nums', data)), 0),
        'count': Coalesce(len(Path('nums', data)), 0)
    }