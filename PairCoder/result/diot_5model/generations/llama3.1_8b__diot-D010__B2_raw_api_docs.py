def nested_mutate_reflects(data, val):
    with Diot(nest=True) as d:
        d.x.y = val
        return d.x.y.get('y', None)