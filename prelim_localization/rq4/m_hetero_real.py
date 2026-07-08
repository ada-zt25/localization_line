#!/usr/bin/env python3
"""
M_hetero-real — REAL (deployable) heterogeneous strong-verifier re-rank (RQ4).

Unlike the oracle-union upper bound (m_hetero_upper.py, which peeks at the gold to
select), this is a DEPLOYABLE verifier: a stronger heterogeneous model
(DeepSeek-V3.2) re-ranks the base pipeline's coverage-filtered candidate set
WITHOUT the gold, from the issue text + candidate code alone. It lower-bounds
(realizes) what the oracle upper bound showed is recoverable.

Setup (S1, crash on-path, n=57, file-given):
  candidate set = the executed lines of the gold file (the on-path filter output,
                  from frozen_subsets.json exec_lines).
  verifier      = DeepSeek-V3.2 ranks the <=10 most-suspicious candidate lines
                  given the issue + numbered candidate code (temperature 0).
Compared, paired, against the cached base Qwen2.5-Coder-32B M4 per-instance hits.

Key handling: reads $T2_API_KEY / $T2_BASE_URL from the gitignored .t2_secrets;
the key is never written to any output or tracked file.
"""
import json, os, re, sys, time, urllib.request, urllib.error, subprocess, random
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC_CACHE = ROOT / "cache" / "src"
SRC_CACHE.mkdir(parents=True, exist_ok=True)
OUT_JSONL = HERE / "results" / "m_hetero_real_perinst.jsonl"
OUT_JSON = HERE / "results" / "m_hetero_real.json"

MODEL = "deepseek-ai/DeepSeek-V3.2"
BASE_URL = os.environ["T2_BASE_URL"].rstrip("/")
API_KEY = os.environ["T2_API_KEY"]
KS = ("R@1", "R@5", "R@10")
SEED = 20260701
N_BOOT = 10000


def http_json(url, data=None, headers=None, timeout=120, retries=6):
    body = json.dumps(data).encode() if data else None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=body, headers=headers or {},
                                         method=("POST" if data else "GET"))
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(min(2 ** attempt + attempt, 30)); continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries - 1:
                time.sleep(min(2 ** attempt, 20)); continue
            raise


def fetch_source(repo, commit, path):
    cache = SRC_CACHE / f"{repo.replace('/', '_')}__{commit[:10]}__{path.replace('/', '_')}"
    if cache.exists():
        return cache.read_text(errors="replace")
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{path}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                txt = r.read().decode(errors="replace")
            cache.write_text(txt)
            return txt
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(2)


def verifier_rank(issue, gold_file, cand_lines, src_lines):
    """Ask DeepSeek-V3.2 to rank the <=10 most-suspicious candidate lines."""
    numbered = "\n".join(f"L{n}: {src_lines[n-1].rstrip()}" for n in cand_lines
                         if 1 <= n <= len(src_lines))
    issue_s = issue.strip()
    if len(issue_s) > 6000:
        issue_s = issue_s[:6000] + "\n...[truncated]"
    sys_p = ("You are an expert Python debugger performing line-level fault localization. "
             "You are given a GitHub issue and the lines of the buggy file that the failing "
             "test actually executed. Identify which of those lines must be edited to fix the "
             "issue. Reason about the root cause, then output your answer.")
    user_p = (f"## Issue\n{issue_s}\n\n## Buggy file: {gold_file}\n"
              f"## Executed candidate lines (line_number: code)\n{numbered}\n\n"
              "Rank the AT MOST 10 candidate line numbers most likely to require editing to "
              "fix this issue, most suspicious first. Output ONLY a JSON array of integers "
              "(the line numbers), e.g. [42, 43, 17]. No prose.")
    body = {"model": MODEL, "temperature": 0, "max_tokens": 400,
            "messages": [{"role": "system", "content": sys_p},
                         {"role": "user", "content": user_p}]}
    d = http_json(f"{BASE_URL}/chat/completions", data=body,
                  headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    txt = d["choices"][0]["message"]["content"]
    m = re.search(r"\[[\s\d,]+\]", txt)
    if not m:
        nums = [int(x) for x in re.findall(r"\bL?(\d{1,6})\b", txt)]
    else:
        nums = [int(x) for x in re.findall(r"\d+", m.group(0))]
    # keep only valid candidate lines, dedup preserve order
    seen, ranked = set(), []
    candset = set(cand_lines)
    for n in nums:
        if n in candset and n not in seen:
            seen.add(n); ranked.append(n)
    return ranked, txt


def hits_at_k(ranked, gold, ks=(1, 5, 10)):
    gold = set(gold)
    return {f"R@{k}": int(any(l in gold for l in ranked[:k])) for k in ks}


def load_qwen_m4_hits():
    d = json.load(open(HERE / "results" / "passB_covnarrow.json"))["results"]
    items = d.values() if isinstance(d, dict) else d
    out = {}
    for it in items:
        a = it["arms"]["ours_dynamic"]
        out[it["instance_id"]] = {k: int(a[k] > 0) for k in KS}
    return out


def load_regions():
    """Qwen's coverage-narrowed region per instance = the candidate set M4 ranked
    (from the cached passB substrate). This is what the verifier must re-rank."""
    d = json.load(open(HERE / "results" / "passB_covnarrow.json"))["results"]
    items = d.values() if isinstance(d, dict) else d
    out = {}
    for it in items:
        sub = it.get("substrate") or {}
        gf = it.get("ranked_files", [None])[0]
        reg = None
        if gf and gf in sub:
            reg = sub[gf].get("region")
        elif len(sub) == 1:
            reg = list(sub.values())[0].get("region")
        if reg:
            out[it["instance_id"]] = sorted(set(reg))
    return out


def paired_boot(a_hits, b_hits, ids, k):
    rng = random.Random(SEED + KS.index(k))
    n = len(ids)
    A = [a_hits[i][k] for i in ids]
    B = [b_hits[i][k] for i in ids]
    ds = []
    for _ in range(N_BOOT):
        s = [rng.randrange(n) for _ in range(n)]
        ds.append(100.0 * (sum(A[j] for j in s) - sum(B[j] for j in s)) / n)
    ds.sort()
    return round(ds[int(0.025 * N_BOOT)], 1), round(ds[int(0.975 * N_BOOT)], 1)


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=HERE, text=True).strip()
    except Exception:
        return "unknown"


def main():
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 8

    frozen = json.load(open(HERE / "frozen_subsets.json"))["S1_crash_onpath"]
    insts = frozen if isinstance(frozen, list) else list(frozen.values())
    pool = {p["instance_id"]: p for p in json.load(open(ROOT / "cache" / "swebench_lite_pool_300.json"))}
    regions = load_regions()

    done = {}
    if OUT_JSONL.exists():
        for line in OUT_JSONL.read_text().splitlines():
            if line.strip():
                r = json.loads(line); done[r["instance_id"]] = r

    todo = [it for it in insts if it["instance_id"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"S1 n={len(insts)}  cached={len(done)}  to-run={len(todo)}  workers={workers}", file=sys.stderr)

    def work(it):
        iid = it["instance_id"]
        gold = json.loads(it["gold_lines"]) if isinstance(it["gold_lines"], str) else it["gold_lines"]
        exec_lines = json.loads(it["exec_lines"]) if isinstance(it["exec_lines"], str) else it["exec_lines"]
        issue = pool[iid].get("problem_statement", "")
        try:
            src = fetch_source(it["repo"], it["base_commit"], it["gold_file"])
            src_lines = src.split("\n")
            # candidate set = Qwen's coverage-narrowed region (what M4 ranked); fall back to exec_lines
            base_cand = regions.get(iid) or exec_lines
            cand = [n for n in base_cand if 1 <= n <= len(src_lines)]
            candset = "region" if iid in regions else "exec_lines_fallback"
            ranked, raw = verifier_rank(issue, it["gold_file"], cand, src_lines)
            h = hits_at_k(ranked, gold)
            return {"instance_id": iid, "ranked": ranked[:10], "gold": gold,
                    "n_cand": len(cand), "candset": candset, "hits": h, "ok": True}
        except Exception as e:
            return {"instance_id": iid, "error": str(e)[:200], "ok": False}

    with open(OUT_JSONL, "a") as fout:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(work, it): it["instance_id"] for it in todo}
            for fut in as_completed(futs):
                r = fut.result()
                done[r["instance_id"]] = r
                fout.write(json.dumps(r) + "\n"); fout.flush()
                tag = r.get("hits") if r.get("ok") else r.get("error")
                print(f"  {r['instance_id']:34s} {tag}", file=sys.stderr)

    # aggregate over instances that ran successfully AND are in S1
    ids = [it["instance_id"] for it in insts if done.get(it["instance_id"], {}).get("ok")]
    qwen = load_qwen_m4_hits()
    ids = [i for i in ids if i in qwen]
    n = len(ids)
    ver_hits = {i: done[i]["hits"] for i in ids}

    def rate(H, k):
        return round(100.0 * sum(H[i][k] for i in ids) / n, 1)

    metrics = {"n": n, "verifier": MODEL,
               "verifier_real": {k: rate(ver_hits, k) for k in KS},
               "base_qwen_M4": {k: rate(qwen, k) for k in KS},
               "delta_verifier_vs_base": {}}
    for k in KS:
        d = round(metrics["verifier_real"][k] - metrics["base_qwen_M4"][k], 1)
        lo, hi = paired_boot(ver_hits, qwen, ids, k)
        metrics["delta_verifier_vs_base"][k] = {"delta_pp": d, "ci95": [lo, hi], "sig": bool(lo > 0 or hi < 0)}

    out = {"config": "M_hetero-real: DEPLOYABLE heterogeneous verifier re-rank (no oracle)",
           "arm": "M_hetero_real", "kind": "deployable_verifier_rerank",
           "model": MODEL, "base_url": BASE_URL, "git_sha": git_sha(),
           "n": n, "seed": SEED, "n_boot": N_BOOT,
           "candidate_set": "coverage-filtered executed lines of the gold file (frozen exec_lines)",
           "metrics": metrics}
    json.dump(out, open(OUT_JSON, "w"), indent=2)
    print(f"\n== M_hetero-real (n={n}) ==")
    print(f"{'k':>5} | {'Qwen2.5 M4':>10} | {'DeepSeek verifier':>17} | {'Δ (real, paired CI)':>22}")
    for k in KS:
        dd = metrics["delta_verifier_vs_base"][k]
        print(f"{k:>5} | {metrics['base_qwen_M4'][k]:>10} | {metrics['verifier_real'][k]:>17} | "
              f"{dd['delta_pp']:>+6} pp {str(dd['ci95']):>12} {'sig' if dd['sig'] else ''}")
    print(f"wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
