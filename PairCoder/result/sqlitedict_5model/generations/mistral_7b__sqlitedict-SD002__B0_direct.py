import sqlite3

def durable_update(items):
    store = make_store()
    store.update(items)
    store.sync()
    conn = sqlite3.connect(store.filename)
    conn.commit()
    return store