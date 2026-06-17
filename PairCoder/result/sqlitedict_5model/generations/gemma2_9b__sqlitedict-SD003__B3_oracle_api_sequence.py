def durable_delete(items, key):
  with make_store() as store:
    store.update(items)
    del store[key]