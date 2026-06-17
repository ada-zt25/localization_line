from bidict import frozenbidict, putall

def make_frozen(pairs):
    with frozenbidict() as b:
        try:
            putall(b, pairs)
            return b
        except (ValueDuplicationError, KeyDuplicationError) as e:
            raise DuplicationError from e