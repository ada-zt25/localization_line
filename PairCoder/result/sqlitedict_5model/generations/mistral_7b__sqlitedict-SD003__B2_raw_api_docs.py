def durable_delete(items, key):
    store = make_store()
    with store:
        for item in items:
            store[item]
        del store[key]
        store.commit()