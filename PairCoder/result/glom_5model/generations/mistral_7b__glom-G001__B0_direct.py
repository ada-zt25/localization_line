from typing import Union
import glom

def deep_get(data: Union[dict, list], path: str) -> Union[str, int, float, bool, None]:
    try:
        return glom.glom(data, path)
    except PathAccessError:
        return None