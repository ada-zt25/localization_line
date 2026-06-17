from contextlib import contextmanager

def nested_mutate_reflects(data, val):
    d = Diot(data)
    with d.thaw() if not d.frozen else d:
        result = d[d.path]
        d[d.path] = val
        return result