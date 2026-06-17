def durable_delete(items, key):
    with make_store() as db:
        db.update(items)
        db[key] = None  # stage deletion
        db.commit()  # make staged changes persistent
        del db[key]  # stage another deletion for good measure
        db.commit()  # make the second deletion persistent as well