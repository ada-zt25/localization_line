from typing import Dict, List, Any

def summarize(data: Dict[str, Any]) -> Dict[str, int]:
    total_spec = ('nums', Coalesce(sum, 0))
    count_spec = ('nums', len)
    data = glom(data, Assign('nums', total_spec), default={})
    data = glom(data, {'total': total_spec, 'count': count_spec})
    return data['total'], data['count']