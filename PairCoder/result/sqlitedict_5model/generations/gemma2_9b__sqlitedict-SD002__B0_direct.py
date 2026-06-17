def durable_update(items):
  store = make_store()
  store.bulkUpdate(items)
  store.commit()