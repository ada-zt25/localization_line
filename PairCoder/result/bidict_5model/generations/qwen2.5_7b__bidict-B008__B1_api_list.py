def atomic_add(bidict, batch):
    try:
        bidict.putall(batch)
        return dict(bidict)
    except DuplicationError:
        return dict(bidict) if isinstance(bidict, (bidict, frozenbidict)) else {}