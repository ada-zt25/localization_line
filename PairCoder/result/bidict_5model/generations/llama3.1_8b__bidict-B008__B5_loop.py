def atomic_add(pairs, batch):
    with bidict() as b:
        try:
            b.putall(batch)
            return dict(b.inv)
        except (ValueDuplicationError, KeyDuplicationError) as e:
            raise DuplicationError from e