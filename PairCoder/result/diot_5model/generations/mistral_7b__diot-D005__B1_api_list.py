from diot import Diot, OrderedDiot, FrozenDiot, DiotFrozenError

def nested_stays_dict(data):
    class NestedDiot(Diot):
        def __init__(self, data, **kwargs):
            super().__init__(OrderedDiot(data), diot_nest=False, **kwargs)

    try:
        diot = NestedDiot(data)
        return diot.to_dict()['x']
    except DiotFrozenError:
        with FrozenDiot(OrderedDiot(data)).thaw():
            diot = NestedDiot(diot, diot_frozen=True)
        return diot.to_dict()['x']