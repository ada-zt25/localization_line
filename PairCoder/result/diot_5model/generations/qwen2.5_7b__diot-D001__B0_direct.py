from diot import Diot

def access_camel(data):
    d = Diot()
    for k, v in data.items():
        if '_' in k:
            new_key = ''.join(word.capitalize() for word in k.split('_'))
            setattr(d, new_key, v)
        else:
            setattr(d, k, v)
    return d.fooBar