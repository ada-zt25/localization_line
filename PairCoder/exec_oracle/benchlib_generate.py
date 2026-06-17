#!/usr/bin/env python3
"""Generic Ollama generation for a benchmark library.

Reads everything (tasks, prompt payloads, gold rules) from the chosen
``lib_<name>`` module, so the same five conditions B0..B4 apply uniformly across
all six libraries (simplug, diot, simpleconf, glom, bidict, sqlitedict).

    python3 benchlib_generate.py --lib glom \
        --models "qwen2.5:7b,qwen2.5-coder:7b,llama3.1:8b,gemma2:9b,mistral:7b" \
        --runs 3 --result-dir result/msgspec_5model

Writes <result-dir>/{prompts,generations}/ and run_config.json. Judge with:
    python3 benchlib_eval.py --result-dir <result-dir>
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import benchlib
import pair_extractor as _pairx

OLLAMA_URL = "http://localhost:11434/api/generate"
# Frontier (OpenAI / OpenAI-compatible) endpoint. The API key is read ONLY from
# the OPENAI_API_KEY environment variable -- never hard-coded, never committed.
# OPENAI_BASE_URL lets you point at a compatible endpoint (e.g. DeepSeek) without
# code changes; it defaults to the official OpenAI v1 base.
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
OPENAI_URL = OPENAI_BASE_URL + "/chat/completions"
# One-shot conditions. B5 is NOT here: the only B5 is the closed loop, produced by
# fair_loop.py (it needs the oracle between rounds; runs leakage-free on a dev/held
# input split rather than as a static prompt).
METHODS = ["B0_direct", "B1_api_list", "B2_raw_api_docs", "B3_oracle_api_sequence",
           "B4_gold_pair_rule"]
DEFAULT_JOBS = max(1, min(5, os.cpu_count() or 4))


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


_EXTRACTED_CACHE: dict = {}


def extracted_rule_for_task(lib, task: dict, top_k: int = 3) -> str:
    """The Phi-extracted pair rule(s) whose relation matches this task's pair_type.

    Injects the top-K by discriminative score (deduped by anchor set), not just
    top-1: the raw scores of true vs false-positive proposals can differ by a tiny
    margin, so top-1 alone can drop the useful rule. Empty string if extraction
    found none for that relation -- B5 then reduces to B1's API list (the honest
    'extraction recovered nothing here' case)."""
    rules = _EXTRACTED_CACHE.get(lib.NAME)
    if rules is None:
        rules = _pairx.extract_library(lib.NAME, platt=None)
        _EXTRACTED_CACHE[lib.NAME] = rules
    cands = sorted((r for r in rules if r["relation"] == task["pair_type"]),
                   key=lambda r: -r["score"])
    seen, parts = set(), []
    for r in cands:
        key = tuple(sorted(r["anchors"]))
        if key in seen:
            continue
        seen.add(key)
        parts.append(r["rule_text"])
        if len(parts) >= top_k:
            break
    return "\n\n".join(parts)


def _env_value(*names: str, default=None):
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return value
    return default


def _env_int(*names: str, default=None):
    value = _env_value(*names, default=None)
    return default if value is None else int(value)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


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


def call_ollama(
    prompt: str,
    model: str,
    temperature: float,
    keep_alive,
    num_predict: int,
    top_p: float,
    num_gpu: int | None = None,
) -> str:
    options = {"temperature": temperature, "num_predict": num_predict, "top_p": top_p}
    if num_gpu is not None:
        options["num_gpu"] = num_gpu
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": options,
    }
    if keep_alive is not None:
        payload["keep_alive"] = keep_alive
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "")


_OPENAI_PREFIXES = ("openai:", "oai:")


def _is_openai_model(model: str) -> bool:
    """Route a model name to the OpenAI provider.

    Explicit ``openai:``/``oai:`` prefix always wins; bare frontier names
    (``gpt-*``, ``gpt4*``, ``chatgpt*``, ``o1/o3/o4*``) are also recognised so a
    --models value like ``gpt-4.1`` just works. Ollama names (``qwen2.5:7b``,
    ``llama3.1:8b``, ...) never match and keep the local path."""
    m = model.lower()
    if m.startswith(_OPENAI_PREFIXES):
        return True
    if m.startswith(("gpt-", "gpt4", "gpt5", "chatgpt")):
        return True
    return re.match(r"^o[1345]([.\-]|$)", m) is not None


def _openai_model_name(model: str) -> str:
    for p in _OPENAI_PREFIXES:
        if model.lower().startswith(p):
            return model[len(p):]
    return model


def call_openai(
    prompt: str,
    model: str,
    temperature: float,
    num_predict: int,
    top_p: float,
) -> str:
    """One chat completion against the OpenAI (or compatible) Chat API.

    Resilient to model-family parameter differences: if the API rejects
    ``max_tokens`` / ``temperature`` / ``top_p`` (newer reasoning models), the
    offending field is swapped or dropped and the request retried. The API key
    is read from OPENAI_API_KEY at call time and never persisted."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set in the environment")
    base = {
        "model": _openai_model_name(model),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": num_predict,
    }
    drop: set[str] = set()
    use_completion_tokens = False
    last_detail = ""
    transient = 0
    MAX_TRANSIENT = 6                     # retries for connection drops / 429 / 5xx
    for _ in range(16):
        body = {k: v for k, v in base.items() if k not in drop}
        if use_completion_tokens:
            body.pop("max_tokens", None)
            body["max_completion_tokens"] = num_predict
        req = urllib.request.Request(
            OPENAI_URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return (data["choices"][0]["message"].get("content") or "")
        except urllib.error.HTTPError as exc:
            last_detail = exc.read().decode("utf-8", "replace")
            low = last_detail.lower()
            if exc.code == 400 and "max_tokens" in low and not use_completion_tokens:
                use_completion_tokens = True
                continue
            if exc.code == 400 and "temperature" in low and "temperature" not in drop:
                drop.add("temperature")
                continue
            if exc.code == 400 and "top_p" in low and "top_p" not in drop:
                drop.add("top_p")
                continue
            if exc.code in (408, 409, 425, 429, 500, 502, 503, 504) and transient < MAX_TRANSIENT:
                transient += 1
                time.sleep(min(2 ** transient, 30))   # exponential backoff, capped
                continue
            # error body is OpenAI's JSON (no key echoed); safe to surface a slice
            raise RuntimeError(f"OpenAI API error {exc.code}: {last_detail[:300]}")
        except (urllib.error.URLError, http.client.HTTPException,
                ConnectionError, TimeoutError) as exc:
            # transient connection-level failure (e.g. RemoteDisconnected): back off + retry
            if transient < MAX_TRANSIENT:
                transient += 1
                time.sleep(min(2 ** transient, 30))
                continue
            raise RuntimeError(f"OpenAI API network error after {transient} retries: {exc!r}")
    raise RuntimeError(f"OpenAI API: exhausted retries ({last_detail[:200]})")


def call_model(
    prompt: str,
    model: str,
    temperature: float,
    keep_alive,
    num_predict: int,
    top_p: float,
    num_gpu: int | None = None,
) -> str:
    """Provider dispatch: OpenAI for frontier names, Ollama otherwise.

    Same signature as call_ollama so existing call sites switch with one rename;
    the Ollama-only args (keep_alive, num_gpu) are ignored on the OpenAI path."""
    if _is_openai_model(model):
        return call_openai(prompt, model, temperature, num_predict, top_p)
    return call_ollama(prompt, model, temperature, keep_alive, num_predict, top_p, num_gpu)


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
    ap.add_argument("--jobs", type=int, default=DEFAULT_JOBS, help="max concurrent model workers")
    ap.add_argument(
        "--keep-alive",
        default=_env_value("GEN_KEEP_ALIVE", "OLLAMA_KEEP_ALIVE", default="1h"),
        help="Ollama keep_alive value (e.g. 1h, 10m, -1, 0)",
    )
    ap.add_argument(
        "--num-predict",
        type=int,
        default=_env_int("GEN_NUM_PREDICT", default=500),
        help="max generated tokens per request",
    )
    ap.add_argument(
        "--top-p",
        type=float,
        default=float(_env_value("GEN_TOP_P", default="0.9")),
        help="top-p sampling value",
    )
    ap.add_argument(
        "--num-gpu",
        type=int,
        default=_env_int("GEN_NUM_GPU", default=None),
        help="optional Ollama num_gpu override (pass only if you know the right value)",
    )
    args = ap.parse_args()

    lib = benchlib.load_lib(args.lib)
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    want = {t.strip() for t in args.tasks.split(",") if t.strip()}
    tasks = [t for t in lib.TASKS if not want or t["task_id"] in want]
    if not tasks:
        raise SystemExit("no tasks selected")

    root = Path(args.result_dir).expanduser().resolve()
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
        "jobs": args.jobs,
        "keep_alive": args.keep_alive,
        "num_predict": args.num_predict,
        "top_p": args.top_p,
        "num_gpu": args.num_gpu,
        "ollama_url": OLLAMA_URL,
    }
    _atomic_write_text(root / "run_config.json", json.dumps(config, indent=2, ensure_ascii=False))

    print(
        f"== generating {lib.NAME} with {min(args.jobs, len(models))} model workers "
        f"(keep_alive={args.keep_alive}, num_predict={args.num_predict}, top_p={args.top_p}) ==",
        flush=True,
    )

    print_lock = threading.Lock()
    jobs: list[dict] = []
    for run_idx in range(args.runs):
        suffix = "" if args.runs == 1 else f"_run{run_idx + 1}"
        for model in models:
            md = safe_name(model)
            for task in tasks:
                for method in methods:
                    payload = method_payload(lib, task, method)
                    prompt = build_prompt(lib, task, payload)
                    name = f"{md}__{task['task_id']}__{method}{suffix}"
                    prompt_path = root / "prompts" / f"{md}__{task['task_id']}__{method}.txt"
                    gen_path = root / "generations" / f"{name}.py"
                    raw_path = root / "generations" / f"{name}.raw.txt"
                    if run_idx == 0:
                        _atomic_write_text(prompt_path, prompt)
                    jobs.append(
                        {
                            "model": model,
                            "run_idx": run_idx + 1,
                            "task_id": task["task_id"],
                            "method": method,
                            "prompt": prompt,
                            "gen_path": gen_path,
                            "raw_path": raw_path,
                        }
                    )

    def run_job(job: dict) -> None:
        with print_lock:
            print(
                f"[run {job['run_idx']}/{args.runs}] {job['model']} {job['task_id']} {job['method']}...",
                flush=True,
            )
        response = ""
        last_exc: Exception | None = None
        for attempt in range(args.retries + 1):
            try:
                response = call_model(
                    job["prompt"],
                    job["model"],
                    args.temperature,
                    args.keep_alive,
                    args.num_predict,
                    args.top_p,
                    args.num_gpu,
                )
            except Exception as exc:
                last_exc = exc
                response = ""
            if response.strip() or attempt == args.retries:
                break
            time.sleep(1)
        if not response.strip() and last_exc is not None:
            with print_lock:
                print(f"  ERROR: {last_exc!r}", flush=True)
        code = extract_code(response) if response.strip() else ""
        _atomic_write_text(job["gen_path"], code)
        _atomic_write_text(job["raw_path"], response)

    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run_job, job) for job in jobs]
        for fut in as_completed(futures):
            fut.result()

    print(f"\nDone. Generations in {root}. Judge with:\n  python3 benchlib_eval.py --result-dir {root}")


if __name__ == "__main__":
    main()
