from diot import Diot

def nested_is_diot(data):
    d = Diot(data)
    return d.x if isinstance(d.x, Diot) else None