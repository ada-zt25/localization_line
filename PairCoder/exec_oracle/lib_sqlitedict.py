#!/usr/bin/env python3
"""Benchmark module: sqlitedict (REAL vendored library, v2.1.0; persistent-store domain).

This library supplies the sixth pair-relation class, completion-obligation, which
the data/config/plugin/extraction libraries do not exhibit. The constraint is a
real, library-specific, runtime-observable obligation: a write to a SqliteDict
(``db[k]=v``) is only durable / visible to another connection AFTER an explicit
``db.commit()`` -- and neither ``close()`` nor the ``with`` block commits
(verified against v2.1.0). Forgetting the partner call (commit) is the
completion-obligation violation, judged by reading the store from a FRESH
connection (never by inspecting source).

Gold pair rules MANUALLY EXTRACTED from sqlitedict's real semantics.
"""

from __future__ import annotations

import fixture_sqlitedict as fx
from fixture_sqlitedict import make_namespace  # noqa: F401  (benchlib interface)

NAME = "sqlitedict"
reset = fx.reset
get_trace = fx.get_trace


def _ok():
    return {"ok": True, "reason": "", "detail": ""}


def _fail(reason, detail):
    return {"ok": False, "reason": reason, "detail": detail}


FUNC_NAMES = {
    "sqlitedict-SD001": "durable_put",
    "sqlitedict-SD002": "durable_update",
    "sqlitedict-SD003": "durable_delete",
}


# ---------------------------------------------------------------------------
# Hidden tests: open a BRAND-NEW connection on the store the function wrote to,
# and check that the intended state survived (i.e. commit() was called). A
# fresh connection sees only committed data, so an un-committed write -> miss
# -> obligation_unmet.
# ---------------------------------------------------------------------------
def _durable_expect(expected_items):
    def check(ret, trace, args):
        path = fx.last_store_path()
        if path is None:
            return _fail("obligation_unmet",
                         "the function never created a store via make_store()")
        fresh = fx.fresh_view(path)
        try:
            present = {k: fresh[k] for k in expected_items if k in fresh}
        finally:
            fresh.close()
        wrong = {k: (expected_items[k], present.get(k, "<absent>"))
                 for k in expected_items if present.get(k) != expected_items[k]}
        if wrong:
            return _fail(
                "obligation_unmet",
                f"a fresh connection cannot see {sorted(wrong)} "
                f"(got {present!r}, expected {expected_items!r}); you must call "
                f"db.commit() after writing -- close()/with do NOT commit")
        return _ok()
    return check


def _check_sd001(ret, trace, args):
    items = args[0]
    return _durable_expect(dict(items))(ret, trace, args)


def _check_sd002(ret, trace, args):
    items = args[0]
    return _durable_expect(dict(items))(ret, trace, args)


def _check_sd003(ret, trace, args):
    items, drop_key = args[0], args[1]
    expected = {k: v for k, v in items.items() if k != drop_key}
    base = _durable_expect(expected)(ret, trace, args)
    if not base["ok"]:
        return base
    # the dropped key must NOT survive in a fresh connection either
    path = fx.last_store_path()
    fresh = fx.fresh_view(path)
    try:
        still_there = drop_key in fresh
    finally:
        fresh.close()
    if still_there:
        return _fail("obligation_unmet",
                     f"the deletion of {drop_key!r} was not committed (a fresh "
                     f"connection still sees it); a delete must also be followed by commit()")
    return _ok()


CHECKS = {
    "sqlitedict-SD001": _check_sd001,
    "sqlitedict-SD002": _check_sd002,
    "sqlitedict-SD003": _check_sd003,
}

INPUTS = {
    "sqlitedict-SD001": [({"a": 1, "b": 2},), ({"x": 10, "y": 20, "z": 30},)],
    "sqlitedict-SD002": [({"a": 1, "b": 2, "c": 3},)],
    "sqlitedict-SD003": [({"a": 1, "b": 2, "c": 3}, "b")],
}


ANCHORS = {
    "sqlitedict-SD001": [
        ("canonical_commit", """
def durable_put(items):
    db = make_store()
    for k, v in items.items():
        db[k] = v
    db.commit()
""", True),
        ("variant_commit_then_close", """
def durable_put(items):
    db = make_store()
    for k, v in items.items():
        db[k] = v
    db.commit()
    db.close()
""", True),
        ("violation_no_commit", """
def durable_put(items):
    db = make_store()
    for k, v in items.items():
        db[k] = v
""", {"obligation_unmet"}),
        ("violation_with_block_no_commit", """
def durable_put(items):
    with make_store() as db:
        for k, v in items.items():
            db[k] = v
""", {"obligation_unmet"}),
        ("violation_close_without_commit", """
def durable_put(items):
    db = make_store()
    for k, v in items.items():
        db[k] = v
    db.close()
""", {"obligation_unmet"}),
    ],
    "sqlitedict-SD002": [
        ("canonical_update_commit", """
def durable_update(items):
    db = make_store()
    db.update(items)
    db.commit()
""", True),
        ("violation_update_no_commit", """
def durable_update(items):
    db = make_store()
    db.update(items)
""", {"obligation_unmet"}),
    ],
    "sqlitedict-SD003": [
        ("canonical_delete_commit", """
def durable_delete(items, key):
    db = make_store()
    for k, v in items.items():
        db[k] = v
    db.commit()
    del db[key]
    db.commit()
""", True),
        ("violation_delete_not_committed", """
def durable_delete(items, key):
    db = make_store()
    for k, v in items.items():
        db[k] = v
    db.commit()
    del db[key]
""", {"obligation_unmet"}),
        ("variant_single_commit_net_state", """
def durable_delete(items, key):
    db = make_store()
    for k, v in items.items():
        db[k] = v
    del db[key]
    db.commit()
""", True),
    ],
}


TASKS = [
    {"task_id": "sqlitedict-SD001", "pair_type": "completion-obligation", "difficulty": "easy",
     "func": "durable_put",
     "task": "Write function durable_put(items). items is a dict. Open a store with make_store(), write every key/value of items into it, and make the writes DURABLE so that a different connection opened on the same store afterwards can read them back."},
    {"task_id": "sqlitedict-SD002", "pair_type": "completion-obligation", "difficulty": "medium",
     "func": "durable_update",
     "task": "Write function durable_update(items). items is a dict. Open a store with make_store(), store all of items in one bulk update, and make the writes durable so a freshly opened connection on the same store sees them."},
    {"task_id": "sqlitedict-SD003", "pair_type": "completion-obligation", "difficulty": "medium",
     "func": "durable_delete",
     "task": "Write function durable_delete(items, key). Open a store with make_store(), store all of items durably, then delete the given key and make that deletion durable too -- a freshly opened connection must see the remaining items and must NOT see the deleted key."},
]

HELPER_LINE = (
    "make_store() is available and returns a fresh SqliteDict (real sqlitedict library) "
    "on its own file; SqliteDict is also available."
)

API_LIST = """Relevant sqlitedict APIs:
- make_store() -> a fresh SqliteDict bound to its own file (autocommit is OFF)
- db[key] = value : stage a write (NOT yet persisted)
- db.update(mapping) : stage many writes at once
- del db[key] : stage a deletion
- db.commit() : PERSIST all staged changes (makes them visible to other connections)
- db.close() : close the connection (does NOT commit pending changes)
- with make_store() as db: ... : context manager (exit does NOT commit either)
"""

RAW_API_DOCS = """Retrieved sqlitedict documentation snippets:
- SqliteDict is a persistent, dict-like store backed by an SQLite file. By default
  autocommit is False, so assignments/updates/deletions are buffered in the current
  transaction until you call commit().
- db.commit() flushes the pending transaction and makes the changes durable and visible
  to other connections; without it the changes are lost when the program ends.
- Closing the database (db.close()) or leaving a `with` block does NOT implicitly commit
  pending changes in this version; you must call db.commit() yourself.
- A freshly opened SqliteDict on the same file reflects only committed data.
"""

# B3*: ABSTRACT call sequence -- the staging ops only; the discharge/commit
# obligation is the pair constraint and is deliberately NOT revealed here.
ORACLE_API_SEQUENCES = {
    "sqlitedict-SD001": "Abstract API sequence (call order only):\nmake_store(); then write each key/value into the store",
    "sqlitedict-SD002": "Abstract API sequence (call order only):\nmake_store(); then store all items in one bulk update",
    "sqlitedict-SD003": "Abstract API sequence (call order only):\nmake_store(); write all items; then delete the given key",
}

# Gold pair rule MANUALLY EXTRACTED from sqlitedict's real semantics.
GOLD_PAIR_RULES = """Relevant API Pair Rules (extracted from sqlitedict semantics):
1. db[k]=v / db.update / del db[k]  ->  db.commit()
Relation: completion-obligation
Constraint: A SqliteDict opened with the default autocommit=False only PERSISTS staged changes (assignments, updates, deletions) when you call db.commit(). If you write but never commit, the changes are NOT durable and a fresh connection on the same file cannot see them. Crucially, db.close() and leaving a `with` block do NOT commit -- so every batch of writes MUST be paired with an explicit db.commit() to discharge the obligation.
Usage pattern:
db = make_store()
db[k] = v
db.commit()        # REQUIRED: close()/with do not commit
"""
