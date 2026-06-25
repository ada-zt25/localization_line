#!/usr/bin/env python3
"""P1 realistic experiment: file NOT given. Two-stage localization on the real
repository, the way an integration must actually work.

Stage 1 (file localization): given the issue + the repo's full Python file list,
the model names the suspect file(s) (top-5).
Stage 2 (line localization): for the gold file IF the model found it, the model
picks the decisive lines (same prompt as P0).

End-to-end line recall = file_hit ? (line recall within gold file) : 0.
This compounds file-localization error into line recall, reproducing the
realistic setting where SWE-Explore measured ~15% line recall.

    OPENAI_BASE_URL=https://api.siliconflow.com/v1 MODEL_BACKEND=openai \
        MODEL=deepseek-ai/DeepSeek-V3 python p1_realistic.py --n 40
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from pathlib import Path
import p0_line_recall as p0

HERE = Path(__file__).resolve().parent

def fetch_tree(repo, commit):
    """All .py file paths in the repo at commit (GitHub trees API, cached)."""
    cache = p0.CACHE / ("tree_" + re.sub(r"[^A-Za-z0-9._-]", "_", f"{repo}_{commit}") + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    url = f"https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1"
    d = json.loads(p0.http_get(url))
    paths = [t["path"] for t in d.get("tree", []) if t.get("type") == "blob" and t["path"].endswith(".py")]
    out = {"paths": paths, "truncated": bool(d.get("truncated"))}
    cache.write_text(json.dumps(out), encoding="utf-8")
    return out

FILE_PROMPT = """You must find which file in a repository needs editing to resolve a GitHub issue.

## Issue
{issue}

## Repository Python files ({nfiles} files)
{filelist}

## Task
Output a JSON array of the file paths MOST LIKELY to need editing, most-likely first, at most 5.
Example: ["pkg/mod.py","pkg/sub/other.py"]. Use paths exactly as listed. JSON only."""

def parse_str_list(text):
    m = re.search(r"\[.*?\]", text, re.S)
    if m:
        try:
            arr = json.loads(m.group(0))
            return [str(x) for x in arr if isinstance(x, str)]
        except Exception:
            pass
    return re.findall(r'"([^"]+\.py)"', text)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--pool", type=int, default=500)
    ap.add_argument("--max-lines", type=int, default=1500)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    backend = os.environ.get("MODEL_BACKEND", "openai")
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")

    rows = p0.load_rows(args.pool)
    import random as _rnd
    _rnd.Random(0).shuffle(rows)   # same order as P0 -> same instances

    selected = []
    for r in rows:
        files = p0.parse_patch(r.get("patch") or "")
        py = [f for f in files if f.endswith(".py")]
        if len(files) != 1 or len(py) != 1 or not files[py[0]]["hunks"]:
            continue
        path = py[0]
        try:
            src = p0.fetch_file(r["repo"], r["base_commit"], path)
        except Exception:
            continue
        if not (0 < len(src.splitlines()) <= args.max_lines):
            continue
        try:
            tree = fetch_tree(r["repo"], r["base_commit"])
        except Exception as e:
            print(f"tree fail {r['instance_id']}: {e}", file=sys.stderr); continue
        if path not in tree["paths"]:
            continue  # gold file must be locatable in the tree
        selected.append((r, path, src, files[path], tree))
        if len(selected) >= args.n:
            break
        time.sleep(0.5)  # be gentle to GitHub
    print(f"selected={len(selected)}", file=sys.stderr)

    results = []
    for i, (r, path, src, gold, tree) in enumerate(selected):
        issue = (r.get("problem_statement") or "")[:6000]
        # ---- stage 1: file localization ----
        filelist = "\n".join(tree["paths"])
        fp = FILE_PROMPT.format(issue=issue, nfiles=len(tree["paths"]), filelist=filelist)
        try:
            fout = p0.call_model(backend, model, fp)
        except Exception as e:
            print(f"[{i}] stage1 fail {e}", file=sys.stderr); continue
        pred_files = parse_str_list(fout)[:args.topk]
        file_hit = path in pred_files
        rank = (pred_files.index(path) + 1) if file_hit else 0
        # ---- stage 2: line localization (only meaningful if file found) ----
        line_recall = 0.0; precision = 0.0; hunk_hit = 0.0
        if file_hit:
            srclines = src.splitlines()
            numbered = "\n".join(f"{j+1}: {ln}" for j, ln in enumerate(srclines))
            lp = p0.PROMPT.format(issue=issue, path=path, numbered=numbered)
            try:
                lout = p0.call_model(backend, model, lp)
                pred, _ = p0.parse_ranges(lout)
                region = gold["region"]; hunks = gold["hunks"]
                line_recall = len(pred & region) / len(region) if region else 0.0
                precision = (len(pred & region) / len(pred)) if pred else 0.0
                hunk_hit = (sum(1 for h in hunks if pred & h) / len(hunks)) if hunks else 0.0
            except Exception as e:
                print(f"[{i}] stage2 fail {e}", file=sys.stderr)
        rec = {"instance_id": r["instance_id"], "repo": r["repo"], "path": path,
               "file_lines": len(src.splitlines()), "n_repo_pyfiles": len(tree["paths"]),
               "truncated_tree": tree["truncated"], "file_hit": file_hit, "file_rank": rank,
               "e2e_line_recall": line_recall, "line_precision": precision, "hunk_hit": hunk_hit}
        results.append(rec)
        print(f"[{i+1}/{len(selected)}] {r['instance_id']:32s} files={len(tree['paths']):>4} "
              f"file_hit={int(file_hit)} rank={rank} e2e_line_rec={line_recall:.2f}", file=sys.stderr)

    def mean(key):
        v = [r[key] for r in results]
        return sum(v) / len(v) if v else 0.0
    summary = {"backend": backend, "model": model, "n": len(results), "topk": args.topk,
               "mean_repo_pyfiles": round(mean("n_repo_pyfiles")),
               "file_hit_rate@%d" % args.topk: round(mean("file_hit"), 3),
               "mean_e2e_line_recall": round(mean("e2e_line_recall"), 3),
               "line_recall_given_file_found": round(
                   (sum(r["e2e_line_recall"] for r in results if r["file_hit"]) /
                    max(1, sum(1 for r in results if r["file_hit"]))), 3)}
    out_path = Path(args.out) if args.out else (HERE / f"p1_{backend}_{model.replace('/','_').replace(':','_')}.json")
    out_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2), encoding="utf-8")
    print("\n==== SUMMARY ====", file=sys.stderr)
    print(json.dumps(summary, indent=2), file=sys.stderr)
    print(f"written: {out_path}", file=sys.stderr)

if __name__ == "__main__":
    main()
