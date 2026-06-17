def durable_put(items):
    with make_store() as db:
        db.update(items)
        db.commit()