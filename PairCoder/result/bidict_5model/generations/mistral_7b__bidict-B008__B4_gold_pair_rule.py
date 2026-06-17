def atomic_add(pairs, batch):
    b = bidict(pairs)
    try:
        b.putall(batch)
        return dict(b)
    except DuplicationError:
        pass  # b unchanged if any pair clashed