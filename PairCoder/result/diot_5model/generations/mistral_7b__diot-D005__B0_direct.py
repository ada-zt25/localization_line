from diot import Diot, OrderedDiot, FrozenDiot

def nested_stays_dict(data):
    class MyDiot(Diot):
        def _convert_value(self, value, key, parent):
            if isinstance(value, dict) and not self._is_frozen(value):
                return OrderedDiot(value)
            return super()._convert_value(value, key, parent)

    return MyDiot().load(data).x