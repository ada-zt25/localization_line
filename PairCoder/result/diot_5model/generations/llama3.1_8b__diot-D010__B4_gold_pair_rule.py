def nested_mutate_reflects(data, val):
    with Diot(data, diot_transform='safe', diot_nest=True) as d:
        d.x.y = val
        return d.x.y