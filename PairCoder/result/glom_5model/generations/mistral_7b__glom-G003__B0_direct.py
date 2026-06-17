from typing import List, Dict
import glom

def pluck_list(data: Dict) -> List[Any]:
    return list(glom.pluck('items.v', data))