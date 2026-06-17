import sqlite3
from sqlitedict import SqliteDict as Store

def durable_put(items):
    store = make_store()
    store.update(items)
    store.sync()