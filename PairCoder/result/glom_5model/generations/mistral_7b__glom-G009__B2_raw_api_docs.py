from typing import List, Dict

def first_item(data: Dict[str, List[Dict[str, str]]]):
    return Coalesce(*[Path('items.{}', default=None)(data)])[0]['v']