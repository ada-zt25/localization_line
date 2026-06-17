from contextlib import contextmanager

def nested_mutate_reflects(data, val):
    d = Diot(data)
    with d.thaw() as d_thawed:
        d_thawed.x.y = val
        return d_thawed.x.y