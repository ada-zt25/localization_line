import re
from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def access_camel(data):
    def camel_case_transform(key):
        return re.sub('_(.)', lambda x: x.group(1).upper(), key)

    diot = OrderedDiot(data, diot_transform=camel_case_transform)
    if isinstance(diot, FrozenDiot):
        with diot.thaw():
            return diot.fooBar
    else:
        return diot.fooBar