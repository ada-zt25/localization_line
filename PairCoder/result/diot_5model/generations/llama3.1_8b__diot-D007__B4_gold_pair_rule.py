def nested_chain(data):
    return Diot(data, diot_transform='safe', diot_nest=True).x.y