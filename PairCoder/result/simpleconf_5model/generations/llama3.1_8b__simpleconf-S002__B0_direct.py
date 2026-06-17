def merge_three(a, b, c, key):
    merged = ProfileConfig()
    merged.load_config(a)
    merged.load_config(b)
    merged.load_config(c)
    return Config(merged).get(key)