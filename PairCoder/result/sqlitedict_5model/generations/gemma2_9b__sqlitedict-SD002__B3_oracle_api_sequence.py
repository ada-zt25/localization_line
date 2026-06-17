def durable_update(items):
  store = make_store()
  store.bulk_update(items)
  store.commit()