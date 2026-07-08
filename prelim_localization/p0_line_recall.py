#!/usr/bin/env python3
"""P0 preliminary experiment: within-file line-level localization recall.

Claim under test: even when handed the CORRECT file, an LLM cannot reliably
pinpoint the decisive lines to edit. We measure the gap between
"found the neighborhood" (hunk/function hit rate, expected HIGH) and
"selected the decisive lines" (exact line recall, expected LOW), on
SWE-bench Verified single-file instances. We run it on a local 7-9B model
and (when OPENAI_API_KEY is set) a frontier model, to test whether the gap
survives at the frontier.

No pip installs: stdlib urllib only. Data via HF datasets-server; base files
via raw.githubusercontent at base_commit.

    MODEL_BACKEND=ollama MODEL=qwen2.5-coder:7b python p0_line_recall.py --n 30
    MODEL_BACKEND=openai MODEL=deepseek-ai/DeepSeek-V3 python p0_line_recall.py --n 30
"""
from __future__ import annotations
import argparse, json, os, re, ssl, sys, time, urllib.request, ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
CTX = ssl.create_default_context()
UA = {"User-Agent": "prelim-loc/0.1"}

# ----------------------------- data access -----------------------------------

def http_get(url, headers=None, timeout=90):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    return urllib.request.urlopen(req, timeout=timeout, context=CTX).read()

_DATASETS = {                                            # ARISE aligns to SWE-bench *Lite*
    "verified": "princeton-nlp/SWE-bench_Verified",
    "lite": "princeton-nlp/SWE-bench_Lite",
    "full": "princeton-nlp/SWE-bench",
}

def load_rows(n_pool=300, dataset=None):
    """Fetch a pool of SWE-bench rows (cached). dataset: 'verified' (default) | 'lite' | 'full',
    or set env SWEBENCH_DATASET. ARISE's口径 = 'lite'. Cache key is per-dataset so verified and
    lite pools never collide (the old 'swebench_verified_pool_N.json' cache stays valid)."""
    import urllib.parse
    ds = (dataset or os.environ.get("SWEBENCH_DATASET", "verified")).strip().lower()
    hf = _DATASETS.get(ds, ds)                            # allow a raw 'org/name' too
    slug = re.sub(r"[^a-z0-9]+", "_", ds).strip("_")
    cache = CACHE / f"swebench_{slug}_pool_{n_pool}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    rows, offset = [], 0
    while len(rows) < n_pool:
        length = min(100, n_pool - len(rows))
        url = ("https://datasets-server.huggingface.co/rows?dataset=" + urllib.parse.quote(hf, safe="")
               + f"&config=default&split=test&offset={offset}&length={length}")
        d = json.loads(http_get(url))
        batch = [r["row"] for r in d.get("rows", [])]
        if not batch:
            break
        rows.extend(batch); offset += len(batch)
    cache.write_text(json.dumps(rows), encoding="utf-8")
    return rows

def fetch_file(repo, commit, path):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", f"{repo}_{commit}_{path}")
    cache = CACHE / ("file_" + safe[-180:])
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="replace")
    raw = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    proxy = os.environ.get("GH_PROXY", "").rstrip("/")   # AutoDL-CN: export GH_PROXY=https://ghproxy.com
    urls = ([f"{proxy}/{raw}"] if proxy else []) + [raw]  # proxy first when set, else direct only
    last = None
    for u in urls:
        try:
            txt = http_get(u).decode("utf-8", "replace")
            cache.write_text(txt, encoding="utf-8")
            return txt
        except Exception as e:
            last = e
    raise last

# --------------------------- patch parsing -----------------------------------

def parse_patch(patch):
    """Return {filepath: {'region': set(orig_lines), 'hunks': [set(orig_lines)]}}.

    region = deleted original lines + anchors around pure insertions (the
    standard "edit-location" set used by SWE-bench localization scoring)."""
    files, cur, old = {}, None, None
    for line in patch.split("\n"):
        if line.startswith("+++ b/"):
            cur = line[6:].strip()
            files.setdefault(cur, {"region": set(), "hunks": [], "deleted": set()})
        elif line.startswith("@@") and cur is not None:
            m = re.search(r"@@ -(\d+)(?:,(\d+))? \+(\d+)", line)
            if m:
                old = int(m.group(1))
                files[cur]["hunks"].append(set())
        elif cur is not None and old is not None:
            if line.startswith("-") and not line.startswith("---"):
                files[cur]["region"].add(old); files[cur]["hunks"][-1].add(old)
                files[cur]["deleted"].add(old); old += 1
            elif line.startswith("+") and not line.startswith("+++"):
                for a in (old - 1, old):  # insertion anchors
                    if a >= 1:
                        files[cur]["region"].add(a); files[cur]["hunks"][-1].add(a)
            elif line.startswith(" "):
                old += 1
    # drop empty hunks
    for f in files.values():
        f["hunks"] = [h for h in f["hunks"] if h]
    return files

_GOLD_PUNCT = set("()[]{},:;\\")   # structural closers/openers — never a localizable target

def clean_gold(gold, flines):
    """ARISE-aligned gold line set: ARISE's gold EXCLUDES context AND blank lines. Our parse_patch
    adds insertion anchors (old-1, old) that frequently land on a BLANK / COMMENT / pure-PUNCTUATION
    line (inserting a method after a blank separator, or anchoring on a lone `)` / `):` continuation)
    — none are localizable code targets. Drop blank, comment, pure-punctuation, and out-of-range
    anchors; the adjacent real code anchor parse_patch already kept (old-1/old pair) is the true
    target (measured 100% best-effort recovery — every non-code anchor has a code line within +-3).
    Measured effect: region-recall ceiling 0.783 -> ~0.896 (~22.6% of raw 'gold' was
    blank/comment/punct/oob), and it makes our Line R@k口径 match ARISE's instead of being harsher.
    NOTE: this is a fraction-of-gold / recall-ceiling correction; binary R@k barely moves because
    region voting never emits blank/comment lines, so they were never hits to begin with."""
    n = len(flines)
    out = set()
    for ln in gold:
        if not (1 <= ln <= n):
            continue
        s = flines[ln - 1].strip()
        if not s or s.startswith("#"):
            continue
        core = s.split("#", 1)[0].strip()                 # ignore any trailing comment
        if core and all(ch in _GOLD_PUNCT for ch in core):
            continue                                      # lone `)`, `):`, `},` etc.
        out.add(ln)
    return out

def line_to_func(src):
    """Map each line number -> enclosing top-level/def name (best effort)."""
    mapping = {}
    try:
        tree = ast.parse(src)
    except Exception:
        return mapping
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            for ln in range(start, end + 1):
                mapping[ln] = node.name
    return mapping

# --------------------------- model adapter -----------------------------------

def call_ollama(model, prompt):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_ctx": 16384}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=600).read())["response"]

def _openai_key():
    k = os.environ.get("OPENAI_API_KEY")
    if k:
        return k.strip()
    f = HERE / ".key"
    if f.exists():
        return f.read_text(encoding="utf-8").strip()
    raise RuntimeError("no OPENAI_API_KEY env and no prelim_localization/.key file")

def call_openai(model, prompt):
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    key = _openai_key()
    body = json.dumps({"model": model, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(base + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            d = json.loads(urllib.request.urlopen(req, timeout=600, context=CTX).read())
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))

def call_model(backend, model, prompt):
    return call_ollama(model, prompt) if backend == "ollama" else call_openai(model, prompt)

# --------------------------- prompt + parse ----------------------------------

PROMPT = """You are localizing the exact code that must be edited to resolve a GitHub issue.

## Issue
{issue}

## File: {path}
This is the ONLY file that needs editing. Its full content is shown with line numbers.

{numbered}

## Task
Output the MINIMAL set of line ranges in THIS file that must be edited to resolve the issue.
Respond with ONLY a JSON array of [start, end] inclusive line ranges (1-indexed), e.g. [[42,45],[88,90]].
No explanation, no prose, JSON only."""

def parse_ranges(text):
    m = re.search(r"\[\s*\[.*?\]\s*\]", text, re.S)
    pairs = []
    if m:
        try:
            for p in json.loads(m.group(0)):
                if isinstance(p, list) and len(p) >= 2:
                    pairs.append((int(p[0]), int(p[1])))
        except Exception:
            pass
    if not pairs:  # fallback: any [a,b]
        for a, b in re.findall(r"\[\s*(\d+)\s*,\s*(\d+)\s*\]", text):
            pairs.append((int(a), int(b)))
    lines = set()
    for a, b in pairs:
        if a > b: a, b = b, a
        if b - a <= 2000:
            lines.update(range(a, b + 1))
    return lines, bool(pairs)

# ------------------------------- main ----------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--pool", type=int, default=300)
    ap.add_argument("--max-lines", type=int, default=500)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    backend = os.environ.get("MODEL_BACKEND", "ollama")
    model = os.environ.get("MODEL", "qwen2.5-coder:7b")

    rows = load_rows(args.pool)
    # deterministic shuffle for repo diversity (dataset is sorted alphabetically)
    import random as _rnd
    _rnd.Random(0).shuffle(rows)
    print(f"pool={len(rows)} instances; selecting single-file Python edits <= {args.max_lines} lines", file=sys.stderr)

    selected = []
    for r in rows:
        files = parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py")]
        if len(files) != 1 or len(py) != 1:
            continue
        path = py[0]
        if not files[path]["hunks"]:
            continue
        try:
            src = fetch_file(r["repo"], r["base_commit"], path)
        except Exception:
            continue
        nlines = len(src.splitlines())
        if nlines == 0 or nlines > args.max_lines:
            continue
        selected.append((r, path, src, files[path]))
        if len(selected) >= args.n:
            break
    print(f"selected={len(selected)}", file=sys.stderr)

    results = []
    for i, (r, path, src, gold) in enumerate(selected):
        srclines = src.splitlines()
        numbered = "\n".join(f"{j+1}: {ln}" for j, ln in enumerate(srclines))
        issue = (r.get("problem_statement") or "")[:6000]
        prompt = PROMPT.format(issue=issue, path=path, numbered=numbered)
        t0 = time.time()
        try:
            out = call_model(backend, model, prompt)
        except Exception as e:
            print(f"[{i}] {r['instance_id']} CALL FAIL {e}", file=sys.stderr)
            continue
        pred, parsed = parse_ranges(out)
        region = gold["region"]
        hunks = gold["hunks"]
        l2f = line_to_func(src)
        gold_funcs = {l2f.get(ln) for ln in region if l2f.get(ln)}
        pred_funcs = {l2f.get(ln) for ln in pred if l2f.get(ln)}
        exact = len(pred & region) / len(region) if region else 0.0
        precision = (len(pred & region) / len(pred)) if pred else 0.0
        loose = (sum(1 for g in region if any(abs(g - p) <= 2 for p in pred)) / len(region)) if region else 0.0
        hunk_hit = (sum(1 for h in hunks if pred & h) / len(hunks)) if hunks else 0.0
        func_hit = (len(gold_funcs & pred_funcs) / len(gold_funcs)) if gold_funcs else None
        over = (len(pred) / len(region)) if region else 0.0
        rec = {"instance_id": r["instance_id"], "repo": r["repo"], "path": path,
               "file_lines": len(srclines), "gold_region": len(region), "n_hunks": len(hunks),
               "pred_lines": len(pred), "parsed": parsed,
               "exact_recall": exact, "precision": precision, "loose_recall": loose, "hunk_hit": hunk_hit,
               "func_hit": func_hit, "over_pred": over, "secs": round(time.time() - t0, 1)}
        results.append(rec)
        print(f"[{i+1}/{len(selected)}] {r['instance_id']:35s} exact={exact:.2f} loose={loose:.2f} "
              f"hunk={hunk_hit:.2f} func={func_hit if func_hit is None else round(func_hit,2)} "
              f"over={over:.1f} ({rec['secs']}s)", file=sys.stderr)

    def mean(key, filt=lambda x: x is not None):
        vals = [r[key] for r in results if filt(r[key])]
        return sum(vals) / len(vals) if vals else 0.0
    summary = {
        "backend": backend, "model": model, "n": len(results),
        "parse_fail": sum(1 for r in results if not r["parsed"]),
        "mean_exact_recall": round(mean("exact_recall"), 3),
        "mean_precision": round(mean("precision"), 3),
        "mean_loose_recall": round(mean("loose_recall"), 3),
        "mean_hunk_hit": round(mean("hunk_hit"), 3),
        "mean_func_hit": round(mean("func_hit"), 3),
        "mean_over_pred": round(mean("over_pred"), 2),
    }
    out_path = Path(args.out) if args.out else (HERE / f"p0_{backend}_{model.replace('/','_').replace(':','_')}.json")
    out_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    print("\n==== SUMMARY ====", file=sys.stderr)
    print(json.dumps(summary, indent=2), file=sys.stderr)
    print(f"written: {out_path}", file=sys.stderr)

if __name__ == "__main__":
    main()
