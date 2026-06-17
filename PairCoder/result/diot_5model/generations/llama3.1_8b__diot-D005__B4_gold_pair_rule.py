def nested_stays_dict(data):
    with FrozenDiot(data, diot_nest=False) as d:
        return d['x']