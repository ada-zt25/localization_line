def access_snake(data):
    d = Diot(data, diot_transform='safe', diot_nest=True)
    with d.thaw():
        return d.foo_bar