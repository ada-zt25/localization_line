def remap(pairs, key, val):
    b = bidict(pairs)
    try:
        b.forceput(key, val)
    except DuplicationError:
        # Handle case where forceput fails (shouldn't happen per problem statement)
        pass
    return dict(b)