def access_snake(data):
    from diot import Diot
    
    d = Diot(data, diot_transform='snake_case')
    return d.foo_bar