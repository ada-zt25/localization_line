def durable_update(items):
    store = make_store()
    with store as db:
        db.update(items)
    store.commit()