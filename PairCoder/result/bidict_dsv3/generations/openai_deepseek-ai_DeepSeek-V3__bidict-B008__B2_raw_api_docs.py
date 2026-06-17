def atomic_add(pairs, batch):
    """Add all (key, value) pairs in batch to pairs bidict atomically.
    If any pair would break the 1:1 mapping, none are applied.
    Returns the resulting plain dict."""
    try:
        pairs.putall(batch)
    except DuplicationError:
        pass
    return dict(pairs)