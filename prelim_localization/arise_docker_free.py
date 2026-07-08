#!/usr/bin/env python3
"""arise_docker_free — run REAL ARISE fault-localization WITHOUT Docker/SWE-agent.

Checks out each repo at base_commit locally (git, no Docker), then drives ARISE's OFFICIAL tools
(the arise_* CLI wrappers on a local checkout) + ARISE's OFFICIAL FL system/instance prompt
(vendor/ARISE/configs/fl.yaml) in a minimal ReAct loop against an OpenAI-compatible LLM.
Emits ARISE's LOCATIONS block per instance -> {iid:[[file,function,line],...]} for stack_arise_spine.py.

Fidelity: uses ARISE's REAL graph + tools + FL prompt; the ONLY non-official part is this ReAct
harness (vs SWE-agent) and local shell (vs Docker) — for FL (no test execution) the repo source is
identical, so the ranking should be close to official. Validate absolute R@1 vs ARISE's 41 before trusting.

Usage:
  OPENAI_BASE_URL=<endpoint> OPENAI_API_KEY=<key> MODEL=<same-as-SPINE> \
    python3 arise_docker_free.py --ids runs/ids_behav132.json --dataset lite --out runs/arise_preds.json \
      [--max-turns 40] [--limit N] [--workers 4]
"""
import os, sys, re, json, subprocess, argparse, urllib.request, ssl, shutil, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "vendor" / "ARISE"
sys.path.insert(0, str(HERE))
import p0_line_recall as p0

CTX = ssl.create_default_context(); CTX.check_hostname = False; CTX.verify_mode = ssl.CERT_NONE
_BIN = VENDOR / "src" / "arise" / "swe_agent_bundle" / "bin"
_VENVPY = VENDOR / ".venv" / "bin"
REPO_ROOT = Path(os.environ.get("ARISE_REPO_CACHE", str(HERE / "arise_repos")))
REPO_ROOT.mkdir(exist_ok=True)

# read the official FL prompt from fl.yaml (system + instance + next-step templates) — hand-parse block scalars (no yaml dep)
_FL = (VENDOR / "configs" / "fl.yaml").read_text()
def _block(name):
    m = re.search(rf"{name}: \|-\n(.*?)(?=\n    \w+_template:|\n  \w+:|\Z)", _FL, re.S)
    if not m: return ""
    lines = m.group(1).split("\n")
    # strip the common 6-space indent of block scalar
    return "\n".join(l[6:] if l.startswith("      ") else l for l in lines).strip("\n")
SYSTEM_T = _block("system_template")
INSTANCE_T = _block("instance_template")
NEXTSTEP_T = _block("next_step_template") or "OBSERVATION:\n{{observation}}"

SAFE = re.compile(r"^\s*(arise_\w+|cat|grep|egrep|rg|find|ls|head|tail|sed|awk|wc|echo|sort|uniq|cut|python3?|nl|pwd|true)\b")

def chat(model, messages, timeout=120, retries=3):
    base = os.environ["OPENAI_BASE_URL"].rstrip("/"); key = os.environ.get("OPENAI_API_KEY", "dummy")
    payload = {"model": model, "temperature": 0, "max_tokens": 1024, "messages": messages}
    ml = model.lower()
    if any(x in ml for x in ("glm", "qwen3", "hunyuan", "ling", "v4")) and "0414" not in ml:
        payload["thinking"] = {"type": "disabled"}
    body = json.dumps(payload).encode()
    import time
    for a in range(retries):
        try:
            req = urllib.request.Request(base + "/chat/completions", data=body,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
            return json.loads(urllib.request.urlopen(req, timeout=timeout, context=CTX).read())["choices"][0]["message"]["content"] or ""
        except Exception:
            if a == retries - 1: raise
            time.sleep(5 * (a + 1))

def checkout(repo, base_commit):
    """git checkout repo@base_commit locally (cached). Returns path or None."""
    d = REPO_ROOT / (repo.replace("/", "__"))
    try:
        if not (d / ".git").exists():
            subprocess.run(["git", "clone", "--filter=blob:none", f"https://github.com/{repo}.git", str(d)],
                           check=True, capture_output=True, timeout=1200)
        subprocess.run(["git", "-C", str(d), "checkout", "-f", base_commit], check=True, capture_output=True, timeout=300)
        # clean untracked so ARISE graph is at base_commit
        subprocess.run(["git", "-C", str(d), "clean", "-fdx"], capture_output=True, timeout=120)
        return d
    except Exception as e:
        print(f"[checkout ERR] {repo}@{base_commit[:8]}: {str(e)[:100]}", file=sys.stderr)
        return None

def run_cmd(cmd, cwd):
    if not SAFE.match(cmd):
        return "ERROR: command not allowed (read-only tools / arise_* only)."
    env = dict(os.environ); env["PATH"] = f"{_VENVPY}:{_BIN}:" + env.get("PATH", "")
    try:
        r = subprocess.run(["bash", "-lc", cmd], cwd=str(cwd), env=env, capture_output=True, text=True, timeout=180)
        return (r.stdout + (("\n[stderr] " + r.stderr) if r.stderr.strip() else ""))[:6000]
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out."
    except Exception as e:
        return f"ERROR: {str(e)[:150]}"

def extract_bash(text):
    m = re.search(r"```(?:bash|sh)?\s*\n(.*?)```", text, re.S)
    return (m.group(1).strip() if m else "")

def parse_locations(text):
    m = re.search(r"LOCATIONS\s*\n(.*?)\nEND_LOCATIONS", text, re.S | re.I)
    if not m: return []
    out, seen = [], set()
    for line in m.group(1).splitlines():
        lm = re.search(r"file\s*:\s*(.+?)\s*,\s*function\s*:\s*(.+?)\s*,\s*line\s*:\s*(\d+)", line, re.I)
        if lm:
            t = (lm.group(1).strip(), lm.group(2).strip(), int(lm.group(3)))
            if t not in seen: seen.add(t); out.append([t[0], t[1], t[2]])
    return out

def localize(iid, row, model, max_turns):
    repo, bc = row["repo"], row["base_commit"]
    d = checkout(repo, bc)
    if not d: return {"instance_id": iid, "error": "checkout_failed", "preds": []}
    issue = (row.get("problem_statement") or "")[:6000]
    sysmsg = SYSTEM_T
    inst = INSTANCE_T.replace("{{working_dir}}", str(d)).replace("{{problem_statement}}", issue)
    messages = [{"role": "system", "content": sysmsg}, {"role": "user", "content": inst}]
    preds = []
    for turn in range(max_turns):
        try:
            resp = chat(model, messages)
        except Exception as e:
            return {"instance_id": iid, "error": f"llm:{str(e)[:60]}", "preds": preds}
        messages.append({"role": "assistant", "content": resp})
        cmd = extract_bash(resp)
        if "LOCATIONS" in (cmd + resp).upper() and "END_LOCATIONS" in (cmd + resp).upper():
            preds = parse_locations(cmd) or parse_locations(resp)
            if preds: break
        if not cmd:
            messages.append({"role": "user", "content": "Emit EXACTLY ONE ```bash code block with a tool command."}); continue
        obs = run_cmd(cmd, d)
        messages.append({"role": "user", "content": NEXTSTEP_T.replace("{{observation}}", obs)})
    return {"instance_id": iid, "turns": turn + 1, "preds": preds}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True); ap.add_argument("--dataset", default="lite")
    ap.add_argument("--out", default=str(HERE / "runs" / "arise_preds.json"))
    ap.add_argument("--max-turns", type=int, default=40); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()
    model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3")
    rows = {r["instance_id"]: r for r in p0.load_rows(500, args.dataset)}
    ids = json.load(open(args.ids)); ids = [i for i in ids if i in rows]
    if args.limit: ids = ids[:args.limit]
    out = Path(args.out); out.parent.mkdir(exist_ok=True)
    done = {r["instance_id"]: r for r in (json.load(open(out)).get("results", []) if out.exists() else [])}
    todo = [i for i in ids if i not in done or not done[i].get("preds")]
    print(f"[arise-df] {len(todo)} to localize (model={model}, {len(ids)} total)", file=sys.stderr)
    results = list(done.values())
    def work(iid): return localize(iid, rows[iid], model, args.max_turns)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for rec in ex.map(work, todo):
            results = [r for r in results if r["instance_id"] != rec["instance_id"]] + [rec]
            done[rec["instance_id"]] = rec
            out.write_text(json.dumps({"model": model, "results": results}, indent=1))
            print(f"  {rec['instance_id']}: {len(rec.get('preds',[]))} locs, turns={rec.get('turns','?')} {rec.get('error','')}", file=sys.stderr)
    # also emit the flat {iid:[[file,func,line]]} that stack_arise_spine.py reads
    flat = {r["instance_id"]: r["preds"] for r in results if r.get("preds")}
    json.dump(flat, open(str(out).replace(".json", "_flat.json"), "w"))
    print(f"[arise-df] wrote {out} + _flat.json ({len(flat)} with preds)", file=sys.stderr)

if __name__ == "__main__":
    main()
