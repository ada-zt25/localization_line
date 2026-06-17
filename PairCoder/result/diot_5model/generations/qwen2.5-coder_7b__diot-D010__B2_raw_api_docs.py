def nested_mutate_reflects(data, val):
    d = Diot(data, diot_nest=True)
    d.x.y = val
    return d.x.y