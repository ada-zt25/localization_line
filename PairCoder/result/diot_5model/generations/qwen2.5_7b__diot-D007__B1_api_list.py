def nested_chain(data):
    d = Diot(data, diot_nest=True)
    try:
        result = d.x.y
    except DiotFrozenError:
        with d.thaw():
            result = d.x.y
    return result