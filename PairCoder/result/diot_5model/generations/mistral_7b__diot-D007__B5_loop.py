import diot

def nested_chain(data):
    d = diot.Diot(data)
    return d.x.y