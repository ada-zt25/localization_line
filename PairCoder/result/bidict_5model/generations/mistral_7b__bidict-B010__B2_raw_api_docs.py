def reject_dup(pairs, key, val):
    bidict = frozenbidict.frozenbidict(pairs)
    try:
        bidict.putall({key: val})
    except DuplicationError:
        pass

    return bidict.to_dict()