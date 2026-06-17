#!/usr/bin/env python3
"""Instrumented execution fixture for the simplug pair-composition tasks.

Provides ``make_score_manager()`` exactly as promised to the model in the
prompts, backed by the REAL simplug library (vendored, v0.5.7), plus
runtime instrumentation that records observable behavior:

- every ``sp.hooks.score(...)`` call, with the set of enabled plugins at
  call time, the forwarded value, and the collected result;
- direct ``sp.get_plugin(name)`` calls and ``wrapper.disable()/enable()``
  calls on the returned wrapper (return-flow evidence at runtime);
- ``sp.disable(...)/sp.enable(...)`` calls;
- ``sp.plugins_context(...)`` entry arguments.

The hidden tests (hidden_tests.py) consume only these runtime observations
plus the function's return value -- never the AST. This breaks the
"injected rule == checked rule" circularity of the static checker.

Design notes
------------
* ``Simplug(project)`` is a per-name singleton, so each call of
  ``make_score_manager()`` uses a fresh unique project name.
* Plugins are fresh classes per manager. Hook impls are written WITHOUT
  ``self`` so the spec/impl signatures match (simplug checks this).
* Score functions are injective per plugin and value-dependent, so the
  result list uniquely identifies WHICH plugins ran and with WHICH value:
      alpha -> ("alpha", value + 1)
      beta  -> ("beta",  value * 2)
      gamma -> ("gamma", value - 3)
* ``sp.disable``/``sp.enable`` are re-implemented on the instance using the
  ORIGINAL (un-instrumented) ``get_plugin``, with identical semantics
  (delegating to ``wrapper.disable()``), so that an ``sp.disable("beta")``
  call does NOT spuriously emit get_plugin/wrapper_disable trace events.
  Only get_plugin calls made by the code under test are traced.
"""

from __future__ import annotations

import itertools
import os
import sys
from pathlib import Path

_VENDOR = str(Path(__file__).resolve().parent / "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

from simplug import Simplug, SimplugResult  # noqa: E402  (vendored, real library)

# ---------------------------------------------------------------------------
# Global runtime trace
# ---------------------------------------------------------------------------

TRACE: list[dict] = []
MANAGERS: list[dict] = []  # [{"label": int, "sp": Simplug}]
_COUNTER = itertools.count()

PLUGIN_NAMES = ("alpha", "beta", "gamma")


def expected_result(name: str, value):
    """The (injective) result each plugin's score hook produces."""
    if name == "alpha":
        return ("alpha", value + 1)
    if name == "beta":
        return ("beta", value * 2)
    if name == "gamma":
        return ("gamma", value - 3)
    raise KeyError(name)


def expected_results(names, value):
    """Hook result list for the given enabled plugins (registration order)."""
    return [expected_result(n, value) for n in PLUGIN_NAMES if n in names]


def reset_trace() -> None:
    del TRACE[:]
    del MANAGERS[:]


def managers_enabled_state() -> dict:
    """Snapshot {label: [enabled plugin names]} for every manager created."""
    return {
        m["label"]: list(m["sp"].get_enabled_plugin_names()) for m in MANAGERS
    }


# ---------------------------------------------------------------------------
# Instrumentation proxies
# ---------------------------------------------------------------------------


class _WrapperProxy:
    """Delegating proxy around SimplugWrapper that logs disable()/enable()."""

    def __init__(self, wrapper, manager_label: int):
        object.__setattr__(self, "_wrapper", wrapper)
        object.__setattr__(self, "_manager_label", manager_label)

    def disable(self):
        TRACE.append(
            {
                "event": "wrapper_disable",
                "manager": self._manager_label,
                "plugin": self._wrapper.name,
            }
        )
        return self._wrapper.disable()

    def enable(self):
        TRACE.append(
            {
                "event": "wrapper_enable",
                "manager": self._manager_label,
                "plugin": self._wrapper.name,
            }
        )
        return self._wrapper.enable()

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_wrapper"), name)

    def __setattr__(self, name, value):
        setattr(object.__getattribute__(self, "_wrapper"), name, value)

    def __eq__(self, other):
        if isinstance(other, _WrapperProxy):
            other = object.__getattribute__(other, "_wrapper")
        return object.__getattribute__(self, "_wrapper") == other

    def __ne__(self, other):
        return not self.__eq__(other)

    # SimplugWrapper defines __eq__ (=> unhashable); mirror that.
    __hash__ = None  # type: ignore[assignment]

    def __repr__(self):
        return repr(object.__getattribute__(self, "_wrapper"))


class _HookProxy:
    """Delegating proxy around the SimplugHook for ``score``.

    Records the enabled-plugin set at call time, the forwarded args/kwargs
    and the collected result (or the exception).
    """

    def __init__(self, hook, sp, manager_label: int):
        object.__setattr__(self, "_hook", hook)
        object.__setattr__(self, "_sp", sp)
        object.__setattr__(self, "_manager_label", manager_label)

    def __call__(self, *args, **kwargs):
        enabled = list(self._sp.get_enabled_plugin_names())
        event = {
            "event": "score",
            "manager": self._manager_label,
            "enabled": enabled,
            "args": args,
            "kwargs": dict(kwargs),
        }
        try:
            result = self._hook(*args, **kwargs)
        except Exception as exc:
            event["error"] = repr(exc)
            TRACE.append(event)
            raise
        event["result"] = result
        TRACE.append(event)
        return result

    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_hook"), name)

    def __repr__(self):
        return f"<instrumented {object.__getattribute__(self, '_hook')!r}>"


# ---------------------------------------------------------------------------
# The fixture promised to the model
# ---------------------------------------------------------------------------


def _build_manager(result_mode):
    """Create a fresh, instrumented Simplug manager with a ``score`` hook and
    three registered plugins.

    Args:
        result_mode: a ``SimplugResult`` deciding how ``sp.hooks.score`` collects
            results. ``ALL_AVAILS`` (default) returns the LIST of every enabled
            plugin's result; ``FIRST``/``LAST`` return a SINGLE result (the
            first/last enabled plugin's, by registration order).

    Returns:
        (sp, alpha, beta, gamma) -- the manager and the three raw plugin
        objects (classes), exactly as the task prompts assume.
    """
    label = next(_COUNTER)
    sp = Simplug(f"paircoder_score_{os.getpid()}_{label}")

    class _Spec:
        @sp.spec(result=result_mode)
        def score(value):
            """Collect a score from every enabled plugin."""

    class Alpha:
        @sp.impl
        def score(value):
            return ("alpha", value + 1)

    class Beta:
        @sp.impl
        def score(value):
            return ("beta", value * 2)

    class Gamma:
        @sp.impl
        def score(value):
            return ("gamma", value - 3)

    sp.register(Alpha, Beta, Gamma)

    # ---- instrumentation (instance-level; library code itself untouched) ----
    orig_get_plugin = sp.get_plugin
    orig_plugins_context = sp.plugins_context

    def traced_get_plugin(name, raw=False):
        wrapper_or_raw = orig_get_plugin(name, raw=raw)
        TRACE.append(
            {
                "event": "get_plugin",
                "manager": label,
                "name": name if isinstance(name, str) else repr(name),
                "raw": raw,
            }
        )
        if raw:
            return wrapper_or_raw
        return _WrapperProxy(wrapper_or_raw, label)

    def traced_disable(*names):
        TRACE.append({"event": "sp_disable", "manager": label, "names": names})
        # identical semantics to Simplug.disable, without tracing get_plugin
        for name in names:
            orig_get_plugin(name).disable()

    def traced_enable(*names):
        TRACE.append({"event": "sp_enable", "manager": label, "names": names})
        for name in names:
            orig_get_plugin(name).enable()

    def traced_plugins_context(plugins):
        # Build a summary WITHOUT consuming one-shot iterables and WITHOUT
        # altering what the real library receives.
        if isinstance(plugins, (list, tuple, set, frozenset)):
            summary = [
                p if isinstance(p, str) else f"<object:{getattr(p, '__name__', type(p).__name__)}>"
                for p in plugins
            ]
        elif isinstance(plugins, dict):
            summary = [repr(k) for k in plugins.keys()]
        else:
            summary = repr(plugins)
        TRACE.append(
            {"event": "plugins_context", "manager": label, "plugins": summary}
        )
        return orig_plugins_context(plugins)

    sp.get_plugin = traced_get_plugin
    sp.disable = traced_disable
    sp.enable = traced_enable
    sp.plugins_context = traced_plugins_context
    sp.hooks._specs["score"] = _HookProxy(sp.hooks._specs["score"], sp, label)

    MANAGERS.append({"label": label, "sp": sp})
    TRACE.append({"event": "make_score_manager", "manager": label})
    return sp, Alpha, Beta, Gamma


def make_score_manager():
    """ALL_AVAILS hook: ``sp.hooks.score(v)`` returns the LIST of results from
    every enabled plugin (registration order, ``None`` filtered)."""
    return _build_manager(SimplugResult.ALL_AVAILS)


def make_first_score_manager():
    """FIRST hook: ``sp.hooks.score(v)`` returns a SINGLE result -- the FIRST
    enabled plugin's, by registration order -- NOT a list."""
    return _build_manager(SimplugResult.FIRST)


def make_last_score_manager():
    """LAST hook: ``sp.hooks.score(v)`` returns a SINGLE result -- the LAST
    enabled plugin's, by registration order -- NOT a list."""
    return _build_manager(SimplugResult.LAST)


# Tasks whose contract requires a non-default score manager. The exec harness
# binds the ambient ``sp`` with the factory named here so the prompt's promise
# ("sp = make_first_score_manager() already exists and is correct") is truthful;
# tasks not listed fall back to the default ALL_AVAILS make_score_manager().
MANAGER_FACTORY_BY_TASK = {
    "simplug-T007": make_first_score_manager,
    "simplug-T008": make_last_score_manager,
}
