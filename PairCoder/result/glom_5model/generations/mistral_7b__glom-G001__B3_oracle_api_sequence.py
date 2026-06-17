from typing import Union, Any
import glom

def deep_get(data: Union[dict, list], path: str) -> Union[Any, None]:
    try:
        return glom.glom(data, Path(path))['']
    except PathAccessError:
        return None