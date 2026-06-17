def durable_delete(items, key):
    with make_store() as db:
        db.update(items)
        db[key] = None  # Staging deletion
        db.commit()
        del db[key]  # Now the deletion is persistent
        db.commit()