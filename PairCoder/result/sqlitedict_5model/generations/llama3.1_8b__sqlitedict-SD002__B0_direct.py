def durable_update(items):
    store = make_store()
    with store.begin(write=True) as transaction:
        store.update(transaction, items)
    store.commit()