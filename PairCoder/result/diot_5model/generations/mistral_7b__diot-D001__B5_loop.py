def access_camel(data):
    def camel_case_transform(key):
        return ''.join([word.capitalize() for word in key.split('_')])

    diot = Diot(data, diot_transform=camel_case_transform)
    return diot.fooBar