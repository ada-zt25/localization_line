def nested_stays_dict(data):
    from diot import Diot

    d = Diot(diot_nest=False)
    d.update(data)
    return d['x']