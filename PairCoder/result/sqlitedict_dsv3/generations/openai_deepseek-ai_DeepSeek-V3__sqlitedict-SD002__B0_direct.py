def durable_update(items):
    store = make_store()
    try:
        store.update(items)
        store.commit()
    finally:
        store.close()