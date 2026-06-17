def merge_three(a, b, c, key):
    merged = a.load() + b.load() + c.load()
    return merged.get(key)