from typing import Union, Any
import glom

def deep_get(data: Union[dict, list], path: str) -> Union[Any, list]:
    try:
        return glom(data, path)
    except PathAccessError:
        return []