from typing import Union

def safe_get(data: T, path: str) -> Union[T, int]:
    try:
        return Coalesce(PathAccessError(-1), Path(path)(data))
    except PathAccessError:
        return -1