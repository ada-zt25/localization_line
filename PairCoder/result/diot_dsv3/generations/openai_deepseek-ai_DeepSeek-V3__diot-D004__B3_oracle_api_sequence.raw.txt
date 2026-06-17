def to_plain_dict(data):
    def convert(obj):
        if isinstance(obj, (Diot, OrderedDiot, FrozenDiot)):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [convert(v) for v in obj]
        else:
            return obj
    
    d = Diot(data)
    return convert(d)