from typing import Union

def safe_get(data: Union[dict, list], path: str) -> Union[int, float, bool, str, None]:
    try:
        return Coalesce(*glom(data, Path(path)))
    except PathAccessError:
        return -1