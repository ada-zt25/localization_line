def to_plain_dict(data):
    return Diot.from_dict(data, nest=False).to_dict()