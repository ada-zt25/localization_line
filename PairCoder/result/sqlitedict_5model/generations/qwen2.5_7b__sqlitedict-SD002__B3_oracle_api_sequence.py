def durable_update(items):
    store = make_store()
    with store.pipe() as pipe:
        pipe.update(items)
    store.sync()