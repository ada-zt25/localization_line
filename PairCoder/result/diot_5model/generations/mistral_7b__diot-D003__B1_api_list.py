from contextlib import contextmanager
import copy

def get_default(data, key):
    def _get_default(diot):
        try:
            return diot[key]
        except KeyError:
            return 0

    diot = Diot(data)
    if diot.frozen:
        with diot.thaw():
            diot = copy.deepcopy(diot)
            diot.frozen = False

    result = _get_default(diot)
    if isinstance(diot, FrozenDiot):
        if diot.frozen:
            raise DiotFrozenError("Tried to modify a frozen diot.")

    return result