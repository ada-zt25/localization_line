def durable_delete(items, key):
    store = make_store()
    for item in items:
        store[item] = None  # Store all items durably
    store.commit()  # Make changes durable and visible to other connections
    del store[key]  # Delete the given key
    store.commit()  # Make deletion durable too