from diot import Diot, OrderedDiot, FrozenDiot

def access_camel(data):
    camel_case_diot = OrderedDiot()
    for key in data:
        snake_case_key = key.replace('_', '.')
        camel_case_diot[snake_case_key] = data[key]
    camel_case_diot = FrozenDiot(camel_case_diot)
    return camel_case_diot['fooBar']