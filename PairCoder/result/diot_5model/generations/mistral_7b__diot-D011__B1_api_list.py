from contextlib import contextmanager

def thaw_to_modify(data, key, val):
    with FrozenDiot(data).thaw() as d:
        try:
            d[key] = val
            return d[key]
        except DiotFrozenError:
            raise ValueError("Cannot modify frozen diot")