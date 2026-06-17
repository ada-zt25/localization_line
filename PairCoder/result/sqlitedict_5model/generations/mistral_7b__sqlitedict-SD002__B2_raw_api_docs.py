import sqlite3

def durable_update(items):
    store = make_store()
    for key, value in items.items():
        store[key] = value
    store.commit()