def durable_delete(items, key):
    store = make_store()
    with store as s:
        for k, v in items.items():
            s[k] = v
        s.commit()
        del s[key]
        s.commit()