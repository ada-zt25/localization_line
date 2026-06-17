from typing import List, Dict

def pluck_list(data: Dict) -> List[str]:
    return list(glom(data, 'items.v'))