from typing import Dict, List, Any
import glom

def summarize(data: Dict[str, Any]) -> Dict[str, int]:
    spec = {'total': Coalesce('nums', 0) + glom.Sum('nums'), 'count': len}
    return glom.glom(data, spec)