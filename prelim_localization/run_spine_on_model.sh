#!/usr/bin/env bash
# run_spine_on_model.sh — run the SPINE behavioral-132 gate on ANY OpenAI-compatible endpoint/model,
# then print the paired M5-vs-vote result under BOTH our clean_gold and the official ARISE gold.
# Purpose: test whether a given backbone (e.g. ARISE's Qwen2.5-Coder-32B) has the backward-reasoning
# capability SPINE needs. NO GPU needed if the endpoint serves the model (API); coverage is cached.
#
# Usage:
#   BASE_URL=<openai-compatible /v1> KEY=<api-key> MODEL=<model-id> TAG=<short-tag> ./run_spine_on_model.sh
# Examples:
#   # AutoDL vLLM (the exact ARISE backbone — also serves your ARISE reproduction):
#   BASE_URL=http://localhost:8002/v1 KEY=dummy MODEL=Qwen/Qwen2.5-Coder-32B-Instruct-AWQ TAG=qwen25coder32b ./run_spine_on_model.sh
#   # OpenRouter / DashScope / Together / Fireworks (any provider that serves it):
#   BASE_URL=https://openrouter.ai/api/v1 KEY=sk-or-... MODEL=qwen/qwen-2.5-coder-32b-instruct TAG=qwen25coder32b ./run_spine_on_model.sh
set -euo pipefail
cd "$(dirname "$0")"
: "${BASE_URL:?set BASE_URL}"; : "${MODEL:?set MODEL}"; : "${TAG:?set TAG}"
export OPENAI_BASE_URL="$BASE_URL"; export OPENAI_API_KEY="${KEY:-dummy}"; export MODEL; export SWEBENCH_DATASET=lite
OUT="runs/spine_behav132_${TAG}.json"

echo "[1/3] endpoint smoke test ($MODEL @ $BASE_URL)"
python3 -c "import sys;sys.path.insert(0,'.');import region_loc as rl;print('  ->', rl._llm_t('$MODEL','Reply with exactly: OK',temperature=0,timeout=45,retries=1)[:20])"

echo "[2/3] SPINE gate on behavioral-132 (coverage cached, no Docker) -> $OUT"
python3 egl_e2e.py --instances runs/ids_behav132.json --reuse-files runs/oracle_behav132.json \
  --coverage --arise-gold --assert-rerank 10 --spine-votebase --dump-ranks --k 5 --workers 4 --out "$OUT"

echo "[3/3] paired M5-vs-vote (clean_gold) + recompute under OFFICIAL ARISE gold"
python3 spine_paired_stats.py "$OUT" --dataset lite | sed -n '/de-noop+de-leak/,/PRIMARY/p'
python3 - "$OUT" <<'PY'
import sys, json, math
sys.path.insert(0,'.'); sys.path.insert(0,'../vendor/ARISE/src')
import p0_line_recall as p0
from arise.eval import gold as ag
rows={r['instance_id']:r for r in p0.load_rows(500,'lite')}
def gs(iid):
    gi=ag.parse_gold(rows[iid].get('patch') or ''); return {(f,l) for f,ls in gi.lines.items() for l in ls}
def hit(rk,g,k):
    s=[]
    for x in rk:
        t=(x[0],x[1])
        if t not in s: s.append(t)
        if len(s)>=k: break
    return 1 if any(t in g for t in s[:k]) else 0
def mc(p):
    w=sum(1 for a,b in p if a and not b);l=sum(1 for a,b in p if b and not a);d=w+l
    return w,l,d,(1.0 if d==0 else round(min(1.0,2*sum(math.comb(d,i) for i in range(min(w,l)+1))/2**d),4))
recs=[r for r in json.load(open(sys.argv[1]))['results'] if r.get('ranks')]
print("  --- under OFFICIAL ARISE gold ---")
for k in (1,5,10):
    pr=[(hit([tuple(x) for x in r['ranks']['ours_m5']],gs(r['instance_id']),k),
         hit([tuple(x) for x in r['ranks']['vote_only']],gs(r['instance_id']),k)) for r in recs if r['ranks'].get('ours_m5') and r['ranks'].get('vote_only')]
    m5=100*sum(a for a,_ in pr)/len(pr); vt=100*sum(b for _,b in pr)/len(pr); w,l,d,pv=mc(pr)
    print(f"  R@{k}: vote={vt:.1f} M5={m5:.1f} Δ={m5-vt:+.1f}pp {w}W/{l}L p={pv}")
PY
echo "done. verdict: if R@1 Δ is clearly + and significant, Qwen2.5-Coder-32B has the reasoning SPINE needs."
