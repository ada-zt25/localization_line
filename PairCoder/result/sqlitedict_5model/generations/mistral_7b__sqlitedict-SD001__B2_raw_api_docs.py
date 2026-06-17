def durable_put(items):
    store = make_store()
    store.update(items)
    store.commit()