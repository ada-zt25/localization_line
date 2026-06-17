from typing import Any, Union

def coalesce_get(data: Any, primary: str, backup: str) -> Union[Any, None]:
    try:
        return data[primary]
    except PathAccessError:
        return data[backup]