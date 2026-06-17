from diot import Diot

def nested_chain(data):
    d = Diot(data)
    return d.x.y