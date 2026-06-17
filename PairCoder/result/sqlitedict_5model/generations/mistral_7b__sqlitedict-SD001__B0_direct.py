import sqlite3

def durable_put(items):
    store = make_store()
    for key, value in items.items():
        store[key] = value
        store.sync()  # Make writes durable
    return store