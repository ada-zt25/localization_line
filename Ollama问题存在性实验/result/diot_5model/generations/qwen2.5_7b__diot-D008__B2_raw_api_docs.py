def todict_then_index(data):
    from diot import Diot

    with Diot(diot_transform='safe', diot_nest=False) as d:
        d.update(data)
        plain_dict = d.to_dict()
        return plain_dict.get('x', {}).get('y')