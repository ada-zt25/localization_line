import re
from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_snake(data):
    def camelcase_to_snake(s):
        return re.sub('(.)([A-Z][a-z]*)', r'\1_\2', s).lower()

    if 'fooBar' in data:
        diot = OrderedDiot({camelcase_to_snake('fooBar'): data['fooBar']})
    else:
        diot = Diot(data, diot_transform=lambda k: camelcase_to_snake(k))

    result = diot.foo_bar

    if isinstance(diot, FrozenDiot):
        with diot.thaw():
            result = diot.get('foo_bar', None)
    return result