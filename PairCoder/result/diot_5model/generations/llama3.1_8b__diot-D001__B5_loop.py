def access_camel(data):
    with FrozenDiot(data, diot_transform='safe', diot_nest=True) as d:
        return d.fooBar