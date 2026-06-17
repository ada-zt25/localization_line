import sqlite3
from sqlitedict import SqliteDict

def durable_update(items):
    store = make_store()
    store.bulk_commit(list(items.items()))
    store.close()
    conn = sqlite3.connect(store.dbpath)
    conn.commit()
    conn.close()