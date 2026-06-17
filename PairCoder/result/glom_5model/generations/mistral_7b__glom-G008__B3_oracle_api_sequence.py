from typing import Union, Any

def assign_return_target(data: Union[T, dict], path: Path, val: Any) -> T:
    Coalesce(glom(data, T(path)), {}).update({Path(path): val})
    return data