def nested_chain(data):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    return d.x.y