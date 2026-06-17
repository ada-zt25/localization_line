def nested_is_diot(data):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    return d.x