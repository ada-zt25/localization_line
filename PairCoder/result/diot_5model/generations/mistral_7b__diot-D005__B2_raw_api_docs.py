from diot import Diot, FrozenDiot

def nested_stays_dict(data):
    diot = Diot(diot_nest=False)
    diot.load(data)
    return diot.thaw().to_dict()['x']