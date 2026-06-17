def nested_mutate_reflects(data, val):
    with FrozenDiot(data) as d:
        if not d.frozen:
            d.x.y = val
        result = d.x.y
    return result