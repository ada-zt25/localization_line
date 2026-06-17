def durable_delete(items, key):
    with make_store() as db:
        db.update({k: v for k, v in items.items()})
        del db[key]
        db.commit()