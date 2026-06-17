def get_default(data, key):
    diot = Diot(data)
    try:
        return diot[key]
    except KeyError:
        return 0

    # If you need to handle frozen diots as well:
    if isinstance(diot, FrozenDiot):
        with diot.thaw() as thawed_diot:
            try:
                return thawed_diot[key]
            except KeyError:
                return 0