#!/usr/bin/env python3
"""Execution fixture for the sqlitedict completion-obligation tasks.

sqlitedict (vendored, v2.1.0) is a real, local, pure-Python persistent dict over
stdlib sqlite3. Its pair constraint is a completion-obligation: a write
(``db[k]=v``) only becomes DURABLE / visible to another connection after an
explicit ``db.commit()`` -- and (verified) neither ``close()`` nor the ``with``
block commits. The obligation violation is therefore runtime-observable: a fresh
connection on the same file cannot see uncommitted writes.

The fixture hands the task code a ``make_store()`` factory that returns a fresh
``SqliteDict`` on a unique temp file (default ``autocommit=False``). After the
function runs, a task's check opens a brand-new connection on that same file
(``fresh_view``) -- simulating another process reading the durable state -- and
verifies the writes survived, i.e. that ``commit()`` was actually called.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from sqlitedict import SqliteDict  # noqa: E402  (vendored, real library)

# Per-evaluation state: a temp dir + the stores created by the code under test.
_TMPDIR: str | None = None
STORES: list[dict] = []   # [{"path": str, "db": SqliteDict}]


def reset() -> None:
    """Fresh temp dir + cleared store list (called before each task input)."""
    global _TMPDIR
    for s in STORES:
        try:
            s["db"].close()
        except Exception:
            pass
    STORES.clear()
    if _TMPDIR and os.path.isdir(_TMPDIR):
        shutil.rmtree(_TMPDIR, ignore_errors=True)
    _TMPDIR = tempfile.mkdtemp(prefix="paircoder_sqlitedict_")


def make_store() -> SqliteDict:
    """A fresh SqliteDict on a unique temp file (autocommit=False, as in real use)."""
    if _TMPDIR is None:
        reset()
    path = os.path.join(_TMPDIR, f"store_{len(STORES)}.sqlite")
    db = SqliteDict(path)
    STORES.append({"path": path, "db": db})
    return db


def last_store_path() -> str | None:
    return STORES[-1]["path"] if STORES else None


def fresh_view(path: str) -> SqliteDict:
    """A brand-new connection on the same file -- sees only COMMITTED state."""
    return SqliteDict(path)


def get_trace() -> list:
    return []


def make_namespace() -> dict:
    """Names injected for generated/anchor code: the real SqliteDict class and the
    make_store() factory promised in the prompts."""
    return {"SqliteDict": SqliteDict, "make_store": make_store}
