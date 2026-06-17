def durable_delete(items, key):
    store = make_store()
    for k, v in items.items():
        store[k] = v
    store.commit()
    del store[key]
    store.commit()
    store.close()