def durable_update(items):
    db = make_store()
    db.update(items)
    db.commit()
    db.close()