def get_default(data, key):
    diot = Diot(data, diot_transform='safe', diot_nest=True)
    return diot.get(key, 0)