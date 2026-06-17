def durable_delete(items, key):
    with make_store() as db:
        db.update(items)
        db.commit()
    with make_store() as db:
        del db[key]
        db.commit()