def to_plain_dict(data):
    diot = Diot(data, diot_transform='safe', diot_nest=True)
    return diot.to_dict()