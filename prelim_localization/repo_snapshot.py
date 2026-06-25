#!/usr/bin/env python3
"""repo_snapshot — a real, read-only working copy of a repo at a given commit, for the
agentic localization harness. Downloads the GitHub archive tarball at base_commit and
extracts it (cached per repo+commit). No git, no Docker — localization only reads the repo.

This is what makes the harness FAITHFULLY agentic: the agent navigates a real checkout
(grep / read / ls) instead of being handed a flat file list (the single-shot shortcut that
puts us in the easy ~0.28 regime instead of the ~0.15 full-agentic regime).

    python repo_snapshot.py pydata/xarray <commit>   # fetch+extract, print root + a grep demo
"""
from __future__ import annotations
import io, os, re, ssl, sys, tarfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
SNAP = HERE / "snapshots"; SNAP.mkdir(exist_ok=True)
_CTX = ssl.create_default_context()
UA = {"User-Agent": "egl-agentic/0.1"}


def snapshot(repo, commit, timeout=600):
    """Return the local root path of repo@commit (download+extract once, then cached)."""
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", f"{repo}_{commit}")
    root = SNAP / safe
    marker = root / ".extracted_ok"
    if marker.exists():
        sub = next((p for p in root.iterdir() if p.is_dir()), None)
        return sub or root
    root.mkdir(parents=True, exist_ok=True)
    url = f"https://codeload.github.com/{repo}/tar.gz/{commit}"
    req = urllib.request.Request(url, headers=UA)
    data = urllib.request.urlopen(req, timeout=timeout, context=_CTX).read()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        for m in tf.getmembers():
            if m.name.startswith("/") or ".." in m.name.split("/"):  # path-traversal guard
                continue
            if not (m.isfile() or m.isdir()):    # skip symlinks/special files (Py3.14 'data' filter rejects them)
                continue
            try:
                tf.extract(m, root, filter="data")
            except Exception:
                pass
    marker.write_text("ok", encoding="utf-8")
    sub = next((p for p in root.iterdir() if p.is_dir()), None)
    return sub or root


def rg_search(root, pattern, max_results=40, globs=("*.py",)):
    """ripgrep over the snapshot -> [(relpath, lineno, text)] (repo-relative paths)."""
    import subprocess, shutil
    root = str(root)
    args = ["rg", "--no-heading", "--line-number", "--color", "never", "-m", str(max_results)]
    for g in globs:
        args += ["-g", g]
    args += [pattern, root]
    if not shutil.which("rg"):
        return _py_search(root, pattern, max_results)
    try:
        out = subprocess.run(args, capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace").stdout
    except Exception:
        return _py_search(root, pattern, max_results)
    res = []
    for line in out.splitlines():
        m = re.match(r"^(.*?):(\d+):(.*)$", line)
        if m:
            rel = os.path.relpath(m.group(1), root).replace("\\", "/")
            res.append((rel, int(m.group(2)), m.group(3)[:300]))
        if len(res) >= max_results:
            break
    return res


def _py_search(root, pattern, max_results):
    rx = re.compile(pattern)
    res = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(dp, fn)
            try:
                for i, ln in enumerate(open(fp, encoding="utf-8", errors="replace"), 1):
                    if rx.search(ln):
                        rel = os.path.relpath(fp, root).replace("\\", "/")
                        res.append((rel, i, ln.rstrip()[:300]))
                        if len(res) >= max_results:
                            return res
            except Exception:
                pass
    return res


def main():
    repo, commit = sys.argv[1], sys.argv[2]
    root = snapshot(repo, commit)
    npy = sum(1 for _ in root.rglob("*.py"))
    print(f"root={root}\n.py files={npy}")
    hits = rg_search(root, r"def \w+", max_results=5)
    print("grep demo (def):")
    for h in hits:
        print("  ", h)


if __name__ == "__main__":
    main()
