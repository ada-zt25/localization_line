#!/usr/bin/env python3
"""Injection-text executability audit (gate before any full run).

The simpleconf bug: a GOLD_PAIR_RULES "Usage pattern:" snippet called a bare
``use_profile(...)`` while the real API is ``ProfileConfig.use_profile(...)``.
Models copy the pattern verbatim -> NameError -> the method's pass rate is
systematically suppressed, silently corrupting the B4-vs-baseline comparison.

This audit re-derives, for every lib, the EXACT namespace the generated code
runs in (``fixture_<lib>.make_namespace()``), extracts the runnable code blocks
from each injected text, and flags any bare call/`with` whose name is not in
that namespace -- especially names that are actually METHODS of an exposed
class (the precise bug signature).

Usage:
    python audit_injection.py                 # all four libs
    python audit_injection.py simpleconf diot # a subset
Exit code is non-zero if any HIGH-severity issue is found.
"""
from __future__ import annotations

import ast
import builtins
import importlib
import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# The six benchmark libraries, all on the uniform lib_<name> interface. pyparam
# was dropped (weak benchmark, see docs/工作进程.md 6.15). Pass a name explicitly
# as an arg to audit any other lib.
LIBS = ["simplug", "diot", "simpleconf", "bidict", "glom", "sqlitedict"]

# Texts that contain copy-pasteable code (prose-only fields are skipped).
CODE_FIELDS = ["GOLD_PAIR_RULES", "API_LIST", "RAW_API_DOCS"]

_BUILTINS = set(dir(builtins)) | {"self", "cls"}


def _namespace_for(lib_name: str) -> dict:
    """The names generated code actually sees at exec time -- exactly what the
    benchlib harness injects via the lib's make_namespace()."""
    lib = importlib.import_module(f"lib_{lib_name}")
    return lib.make_namespace()


def _method_owners(ns: dict) -> dict[str, list[str]]:
    """Map public method/attr name -> list of exposed class names that own it."""
    owners: dict[str, list[str]] = {}
    for name, obj in ns.items():
        # for a class, its own attrs; for an instance, its type's attrs
        cls = obj if isinstance(obj, type) else type(obj)
        if cls.__module__ == "builtins":
            continue  # ignore str/int/etc. methods of plain data values
        for attr in dir(cls):
            if not attr.startswith("_"):
                owners.setdefault(attr, []).append(name)
    return owners


def _extract_usage_blocks(text: str) -> list[str]:
    """Pull the code block following each 'Usage pattern:' marker.

    A block runs from the line after the marker until a blank line or the next
    numbered rule (e.g. '2. ...'). Multi-line (with-blocks) are kept together.
    """
    blocks: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].strip().lower().startswith("usage pattern"):
            i += 1
            buf: list[str] = []
            while i < len(lines):
                ln = lines[i]
                if ln.strip() == "" or re.match(r"^\s*\d+\.\s", ln):
                    break
                buf.append(ln)
                i += 1
            if buf:
                blocks.append("\n".join(buf))
        else:
            i += 1
    return blocks


def _bare_calls(block: str) -> set[str]:
    """Names invoked as bare calls or `with NAME(...)` (func is ast.Name)."""
    src = textwrap.dedent(block)
    try:
        tree = ast.parse(src)
    except SyntaxError:
        # fall back: parse each physical line independently
        names: set[str] = set()
        for ln in src.splitlines():
            try:
                names |= _bare_calls_tree(ast.parse(textwrap.dedent(ln)))
            except SyntaxError:
                pass
        return names
    return _bare_calls_tree(tree)


def _bare_calls_tree(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            names.add(node.func.id)
    return names


def audit_lib(lib_name: str) -> list[tuple[str, str]]:
    """Return list of (severity, message) issues for one lib."""
    lib = importlib.import_module(f"lib_{lib_name}")
    ns = _namespace_for(lib_name)
    owners = _method_owners(ns)
    issues: list[tuple[str, str]] = []

    for field in CODE_FIELDS:
        text = getattr(lib, field, None)
        if not isinstance(text, str):
            continue
        for block in _extract_usage_blocks(text):
            for name in _bare_calls(block):
                if name in ns or name in _BUILTINS:
                    continue
                if name in owners:
                    classes = " / ".join(f"{c}.{name}" for c in owners[name])
                    issues.append((
                        "HIGH",
                        f"{field}: bare call `{name}(...)` is not in the exec "
                        f"namespace; real API is {classes} -> NameError at runtime",
                    ))
                else:
                    # likely a local helper/constructor defined in the snippet,
                    # or a data placeholder used as a call -- worth a look, low risk.
                    issues.append((
                        "INFO",
                        f"{field}: bare call `{name}(...)` not in namespace "
                        f"(may be a snippet-local name)",
                    ))
    return issues


def main(argv: list[str]) -> int:
    libs = argv or LIBS
    high = 0
    for lib_name in libs:
        try:
            issues = audit_lib(lib_name)
        except ModuleNotFoundError as e:
            print(f"[skip] {lib_name}: cannot import ({e.name}); skipped")
            continue
        highs = [m for sev, m in issues if sev == "HIGH"]
        infos = [m for sev, m in issues if sev == "INFO"]
        status = "FAIL" if highs else "ok"
        print(f"[{status:4}] {lib_name}: {len(highs)} high, {len(infos)} info")
        for m in highs:
            print(f"    HIGH  {m}")
        for m in infos:
            print(f"    info  {m}")
        high += len(highs)
    print("-" * 60)
    if high:
        print(f"AUDIT FAILED: {high} high-severity executability issue(s). "
              f"Fix the injected text before any full run.")
        return 1
    print("AUDIT PASSED: all injected usage patterns are executable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
