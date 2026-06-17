def to_plain_dict(data):
    diot_data = Diot(data, diot_transform='safe', diot_nest=True)
    return diot_data.to_dict()