from typing import Union, Any

def assign_in_place(data: Union[Any, list, dict], path: str, val: Any) -> Any:
    spec = Coalesce(*Path.parts(path))
    Assign(glom(data, spec), val)
    return glom(data, spec)