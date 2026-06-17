def durable_delete(items, key):
    with make_store() as db:
        for k, v in items.items():
            db[k] = v
        db.commit()
    
    with make_store() as db:
        del db[key]
        db.commit()