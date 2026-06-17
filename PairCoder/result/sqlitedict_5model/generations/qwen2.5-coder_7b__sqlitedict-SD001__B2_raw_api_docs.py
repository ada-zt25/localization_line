def durable_put(items):
    with make_store() as db:
        for key, value in items.items():
            db[key] = value
        db.commit()