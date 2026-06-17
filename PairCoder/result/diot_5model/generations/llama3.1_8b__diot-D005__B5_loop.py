def nested_stays_dict(data):
    with Diot(data, diot_transform='safe', diot_nest=False) as d:
        return d['x']