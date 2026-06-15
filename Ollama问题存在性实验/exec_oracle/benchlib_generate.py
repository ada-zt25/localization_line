#!/usr/bin/env python3
"""Generic Ollama generation for a benchmark library (msgspec/peewee/niquests).

Mirrors paircoder_step0_simplug_pilot's generation loop but reads everything
(tasks, prompts payloads, gold rules) from the chosen ``lib_<name>`` module, so
the same five conditions B0..B4 apply uniformly across libraries.

    python3 benchlib_generate.py --lib msgspec \
        --models "qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b" \
        --runs 3 --result-dir result/msgspec_5model

Writes <result-dir>/{prompts,generations}/ and run_config.json. Judge with:
    python3 benchlib_eval.py --result-dir <result-dir>
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

import benchlib

OLLAMA_URL = "http://localhost:11434/api/generate"
METHODS = ["B0_direct", "B1_api_list", "B2_raw_api_docs", "B3_oracle_api_sequence", "B4_gold_pair_rule"]


_RULES_BY_RELATION_CACHE: dict[str, dict[str, str]] = {}


def _split_pair_rules(block: str) -> dict[str, str]:
    """Split a GOLD_PAIR_RULES block into {relation: full_rule_text}.

    Each numbered rule carries a ``Relation: <name>`` line. B4 injects only the
    rule whose relation matches the task's pair_type rather than dumping all
    rules -- the all-rules dump leaks irrelevant usage patterns into tasks that
    must not use them (see the simplug config-return regression)."""
    body = block.split("\n", 1)[1] if "\n" in block else block
    rules: dict[str, str] = {}
    for chunk in re.split(r"\n(?=\d+\.\s)", body):
        m = re.search(r"Relation:\s*(\S+)", chunk)
        if m:
            rules[m.group(1)] = chunk.strip()
    return rules


def gold_rule_for_task(lib, task: dict) -> str:
    """The single gold pair rule matching this task's pair_type."""
    rules = _RULES_BY_RELATION_CACHE.get(lib.NAME)
    if rules is None:
        rules = _split_pair_rules(lib.GOLD_PAIR_RULES)
        _RULES_BY_RELATION_CACHE[lib.NAME] = rules
    relation = task["pair_type"]
    rule = rules.get(relation)
    if rule is None:
        raise KeyError(
            f"{lib.NAME}: no gold pair rule for pair_type {relation!r}; "
            f"known: {sorted(rules)}"
        )
    return "Relevant API Pair Rule:\n" + rule


def method_payload(lib, task: dict, method: str) -> str:
    if method == "B0_direct":
        return ""
    if method == "B1_api_list":
        return lib.API_LIST
    if method == "B2_raw_api_docs":
        return lib.RAW_API_DOCS
    if method == "B3_oracle_api_sequence":
        return lib.ORACLE_API_SEQUENCES[task["task_id"]]
    if method == "B4_gold_pair_rule":
        # B4 = B1's API knowledge PLUS this task's pair rule, so B4 is a strict
        # superset of B1 and B4-B1 isolates the pair rule's marginal value.
        # Only the relevant rule is added (no cross-task pattern contamination).
        return lib.API_LIST + "\n\n" + gold_rule_for_task(lib, task)
    raise KeyError(method)


def build_prompt(lib, task: dict, payload: str) -> str:
    return f"""You are writing Python code using the {lib.NAME} library.
Return only Python code. Do not include Markdown fences. Do not explain.

Assume the following already exist and are correct:
{lib.HELPER_LINE}

Task:
{task["task"]}

{payload}

Requirements:
- Define only the function {task["func"]}.
- Do not redefine the provided helpers.
- Use the provided helpers/objects.
- Return only executable Python code.
"""


def call_ollama(prompt: str, model: str, temperature: float) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_predict": 500, "top_p": 0.9},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "")


def extract_code(text: str) -> str:
    fenced = re.findall(r"```(?:python)?\s*(.*?)```", text, flags=re.S | re.I)
    if fenced:
        return fenced[0].strip()
    starts = [i for i in [text.find("def "), text.find("from "), text.find("import ")] if i >= 0]
    return text[min(starts):].strip() if starts else text.strip()


def safe_name(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace(",", "__")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generic Ollama generation for a benchmark library.")
    ap.add_argument("--lib", required=True)
    ap.add_argument("--models", default="qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b")
    ap.add_argument("--methods", default=",".join(METHODS))
    ap.add_argument("--tasks", default="", help="optional comma-separated task ids (smoke test)")
    ap.add_argument("--result-dir", required=True)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()

    lib = benchlib.load_lib(args.lib)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    want = {t.strip() for t in args.tasks.split(",") if t.strip()}
    tasks = [t for t in lib.TASKS if not want or t["task_id"] in want]
    if not tasks:
        raise SystemExit("no tasks selected")

    root = Path(args.result_dir)
    (root / "prompts").mkdir(parents=True, exist_ok=True)
    (root / "generations").mkdir(parents=True, exist_ok=True)

    config = {
        "lib": args.lib,
        "models": models,
        "methods": methods,
        "tasks": [t["task_id"] for t in tasks],
        "task_meta": {
            t["task_id"]: {"pair_type": t.get("pair_type", ""), "difficulty": t.get("difficulty", "")}
            for t in tasks
        },
        "temperature": args.temperature,
        "runs": args.runs,
        "ollama_url": OLLAMA_URL,
    }
    (root / "run_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    for run_idx in range(args.runs):
        suffix = "" if args.runs == 1 else f"_run{run_idx + 1}"
        for model in models:
            md = safe_name(model)
            for task in tasks:
                for method in methods:
                    payload = method_payload(lib, task, method)
                    prompt = build_prompt(lib, task, payload)
                    if run_idx == 0:
                        (root / "prompts" / f"{md}__{task['task_id']}__{method}.txt").write_text(
                            prompt, encoding="utf-8"
                        )
                    print(f"[run {run_idx+1}/{args.runs}] {model} {task['task_id']} {method}...", flush=True)
                    try:
                        response = ""
                        for attempt in range(args.retries + 1):
                            response = call_ollama(prompt, model, args.temperature)
                            if response.strip() or attempt == args.retries:
                                break
                            time.sleep(1)
                        code = extract_code(response)
                    except Exception as exc:
                        response, code = "", ""
                        print(f"  ERROR: {exc!r}", flush=True)
                    name = f"{md}__{task['task_id']}__{method}{suffix}"
                    (root / "generations" / f"{name}.py").write_text(code, encoding="utf-8")
                    (root / "generations" / f"{name}.raw.txt").write_text(response, encoding="utf-8")

    print(f"\nDone. Generations in {root}. Judge with:\n  python3 benchlib_eval.py --result-dir {root}")


if __name__ == "__main__":
    main()
