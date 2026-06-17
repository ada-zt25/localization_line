from typing import Dict, List, Any

def summarize(data: Dict[str, Any]) -> Dict[str, Any]:
    total_spec = Coalesce('nums.sum', lambda: 0)
    count_spec = Coalesce('nums.len', lambda: 0)

    data = Assign('nums', glom(data, 'nums', default=[]))

    data = Assign('total', total_spec(data))
    data = Assign('count', count_spec(data))

    return data