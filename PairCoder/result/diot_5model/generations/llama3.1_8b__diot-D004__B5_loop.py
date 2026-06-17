def to_plain_dict(data):
    with FrozenDiot(data) as frozen_diot:
        return frozen_diot.to_dict()