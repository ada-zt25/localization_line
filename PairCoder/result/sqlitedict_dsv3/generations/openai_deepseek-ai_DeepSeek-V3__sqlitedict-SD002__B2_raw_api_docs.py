def durable_update(items):
    with make_store() as store:
        for key, value in items.items():
            store[key] = value
        store.commit()