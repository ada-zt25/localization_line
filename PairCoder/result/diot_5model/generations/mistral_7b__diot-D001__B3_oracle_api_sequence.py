from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_camel(data):
    camel_case_diot = OrderedDiot(FrozenDiot(data), camel_to_snake)
    try:
        return camel_case_diot.fooBar
    except DiotFrozenError:
        raise ValueError("The provided data does not contain the key 'foo_bar'")