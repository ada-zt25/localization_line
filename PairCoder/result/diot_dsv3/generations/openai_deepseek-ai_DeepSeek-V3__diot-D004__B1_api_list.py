def to_plain_dict(data):
    diot = Diot(data, diot_nest=True)
    return diot.to_dict()