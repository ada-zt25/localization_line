def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except KeyDuplicationError:
        pass  # ignore if key already exists in the mapping
    return dict(b.inv)