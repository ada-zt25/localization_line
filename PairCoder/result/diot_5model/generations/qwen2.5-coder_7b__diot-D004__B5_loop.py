def to_plain_dict(data):
    return Diot(data, diot_transform='safe', diot_nest=False).to_dict()