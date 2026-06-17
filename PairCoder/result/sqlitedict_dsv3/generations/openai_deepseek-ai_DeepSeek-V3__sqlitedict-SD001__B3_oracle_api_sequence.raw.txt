def durable_put(items):
    store = make_store()
    try:
        for key, value in items.items():
            store[key] = value
        store.commit()
    finally:
        store.close()