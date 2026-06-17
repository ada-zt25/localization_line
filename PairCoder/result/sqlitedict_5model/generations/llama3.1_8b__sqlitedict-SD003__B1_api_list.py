def durable_delete(items, key):
    with make_store() as db:
        for item in items:
            db[item] = None  # Stage writes
        db.update(items)  # Stage many writes at once
        del db[key]  # Stage deletion
        db.commit()  # Persist all staged changes