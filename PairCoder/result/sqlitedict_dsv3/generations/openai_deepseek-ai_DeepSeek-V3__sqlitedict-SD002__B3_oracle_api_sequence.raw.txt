def durable_update(items):
    store = make_store()
    store.update(items)
    store.commit()
    store.close()