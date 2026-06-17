def nested_is_diot(data):
    return Diot(data, diot_transform='safe', diot_nest=True).x