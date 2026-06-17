def durable_delete(items, key):
    with make_store() as db:
        db.update(items)  # stage many writes at once
        db[key] = None  # stage a write (NOT yet persisted)
        db.commit()  # PERSIST all staged changes (makes them visible to other connections)
        del db[key]  # delete the given key
        db.commit()  # make deletion durable too