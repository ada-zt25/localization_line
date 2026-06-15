#!/usr/bin/env python3
"""
Step 0 controlled pilot for PairCoder on simplug.

This focuses on pairwise composition errors that are harder than watchdog's
well-known lifecycle pattern:
- plugins_context([...]) -> hooks.<hook>() parameter semantics
- get_plugin(name) -> wrapper.disable()/enable() return-flow
- disable/enable(name) -> hooks.<hook>() shared-receiver/state dependency

The tasks assume a helper exists:
    sp, alpha, beta, gamma = make_score_manager()
where sp is a Simplug manager with a score hook and registered plugins.
"""

from __future__ import annotations

import ast
import argparse
import csv
import json
import os
import re
import time
import urllib.request
from pathlib import Path


DEFAULT_MODELS = os.environ.get("PAIRCODER_OLLAMA_MODELS", "qwen2.5:7b,qwen2.5-coder:7b")
DEFAULT_MODEL = os.environ.get("PAIRCODER_OLLAMA_MODEL", "qwen2.5:7b")
DEFAULT_METHODS = os.environ.get(
    "PAIRCODER_METHODS",
    "B0_direct,B1_api_list,B2_raw_api_docs,B3_oracle_api_sequence,B4_gold_pair_rule",
)
OLLAMA_URL = "http://localhost:11434/api/generate"


TASKS = [
    {
        "task_id": "simplug-T001",
        "pair_type": "param-dependency",
        "difficulty": "easy",
        "task": "Write function only_beta_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Run sp.hooks.score(value) with only the beta plugin enabled temporarily, then return the hook result.",
        "expect_context_names": {"beta"},
    },
    {
        "task_id": "simplug-T002",
        "pair_type": "param-dependency",
        "difficulty": "medium",
        "task": "Write function only_alpha_gamma_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Run sp.hooks.score(value) with only alpha and gamma enabled temporarily, then return the hook result.",
        "expect_context_names": {"alpha", "gamma"},
    },
    {
        "task_id": "simplug-T003",
        "pair_type": "shared-receiver",
        "difficulty": "easy",
        "task": "Write function disable_beta_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Disable beta by name, then call sp.hooks.score(value), and return the result.",
        "expect_disable_name": "beta",
    },
    {
        "task_id": "simplug-T004",
        "pair_type": "return-flow",
        "difficulty": "medium",
        "task": "Write function get_beta_wrapper_disable_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Get beta's plugin wrapper from the manager, disable that wrapper, then call sp.hooks.score(value), and return the result.",
        "expect_get_plugin_wrapper": "beta",
    },
    {
        "task_id": "simplug-T005",
        "pair_type": "lifecycle",
        "difficulty": "hard",
        "task": "Write function beta_only_inside_context_then_all_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. First collect sp.hooks.score(value) inside a temporary context where only beta is enabled. Then after the context exits, collect sp.hooks.score(value) again with the original plugin state restored. Return both results.",
        "expect_context_names": {"beta"},
        "expect_two_hook_calls": True,
    },
    {
        "task_id": "simplug-T006",
        "pair_type": "shared-receiver",
        "difficulty": "medium",
        "task": "Write function disable_alpha_gamma_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Disable alpha and gamma by name, then call sp.hooks.score(value), and return the result.",
        "expect_disable_names": {"alpha", "gamma"},
    },
    # --- expansion: 5th pair type (config -> return-contract) + rebalance ---
    {
        "task_id": "simplug-T007",
        "pair_type": "config-return-contract",
        "difficulty": "easy",
        "task": "Write function first_score(value). Use make_first_score_manager() to get sp, alpha, beta, gamma. Call sp.hooks.score(value) and return its result directly.",
        "helper": "sp, alpha, beta, gamma = make_first_score_manager()",
    },
    {
        "task_id": "simplug-T008",
        "pair_type": "config-return-contract",
        "difficulty": "medium",
        "task": "Write function last_score(value). Use make_last_score_manager() to get sp, alpha, beta, gamma. Call sp.hooks.score(value) and return its result directly.",
        "helper": "sp, alpha, beta, gamma = make_last_score_manager()",
    },
    {
        "task_id": "simplug-T009",
        "pair_type": "return-flow",
        "difficulty": "hard",
        "task": "Write function disable_alpha_gamma_via_wrappers_then_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. Get the plugin wrapper for alpha and disable it, then get the plugin wrapper for gamma and disable it, then call sp.hooks.score(value), and return the result.",
    },
    {
        "task_id": "simplug-T010",
        "pair_type": "lifecycle",
        "difficulty": "hard",
        "task": "Write function persistent_disable_beta_then_temp_only_alpha_score(value). Use make_score_manager() to get sp, alpha, beta, gamma. First disable beta by name. Then, inside a temporary context where only alpha is enabled, collect sp.hooks.score(value). After the context exits, collect sp.hooks.score(value) again. Return both results (inside, after).",
        # No static expect_* fields: the correct solution legitimately combines
        # sp.disable + plugins_context, an interaction the static checker cannot
        # model -- judged by the execution oracle only.
    },
]


API_LIST = """Relevant simplug APIs:
- from simplug import Simplug
- make_score_manager() -> returns (sp, alpha, beta, gamma)
- make_first_score_manager() -> like make_score_manager, score hook uses result=FIRST
- make_last_score_manager() -> like make_score_manager, score hook uses result=LAST
- sp.plugins_context(plugins): context manager that temporarily changes enabled plugins.
- sp.hooks.score(value): calls the score hook and returns collected results.
- sp.disable(*names): disable plugins.
- sp.enable(*names): enable plugins.
- sp.get_plugin(name): get a plugin wrapper.
- wrapper.disable(): disable this plugin wrapper.
- wrapper.enable(): enable this plugin wrapper.
"""


RAW_API_DOCS = """Retrieved simplug documentation snippets:
- make_score_manager() returns a Simplug manager and plugin objects: sp, alpha, beta, gamma.
- make_first_score_manager()/make_last_score_manager() return a manager whose score hook is declared with result=SimplugResult.FIRST/LAST.
- A hook's result mode controls what hooks.<name>(...) returns: ALL_AVAILS returns a list of every enabled plugin's result; FIRST/LAST return a single result (the first/last enabled plugin's).
- plugins_context(plugins) creates a temporary plugin context and restores the previous plugin state after the context exits.
- hooks.score(value) invokes the score hook through the manager and returns the collected hook results.
- disable(*names) disables plugins on the manager.
- enable(*names) enables plugins on the manager.
- get_plugin(name) returns a plugin wrapper object for a registered plugin.
- wrapper.disable() disables the plugin represented by that wrapper.
- wrapper.enable() enables the plugin represented by that wrapper.
"""


ORACLE_API_SEQUENCES = {
    "simplug-T001": "Oracle API sequence:\nmake_score_manager -> sp.plugins_context -> sp.hooks.score",
    "simplug-T002": "Oracle API sequence:\nmake_score_manager -> sp.plugins_context -> sp.hooks.score",
    "simplug-T003": "Oracle API sequence:\nmake_score_manager -> sp.disable -> sp.hooks.score",
    "simplug-T004": "Oracle API sequence:\nmake_score_manager -> sp.get_plugin -> wrapper.disable -> sp.hooks.score",
    "simplug-T005": "Oracle API sequence:\nmake_score_manager -> sp.plugins_context -> sp.hooks.score -> sp.hooks.score",
    "simplug-T006": "Oracle API sequence:\nmake_score_manager -> sp.disable -> sp.hooks.score",
    "simplug-T007": "Oracle API sequence:\nmake_first_score_manager -> sp.hooks.score",
    "simplug-T008": "Oracle API sequence:\nmake_last_score_manager -> sp.hooks.score",
    "simplug-T009": "Oracle API sequence:\nmake_score_manager -> sp.get_plugin -> wrapper.disable -> sp.get_plugin -> wrapper.disable -> sp.hooks.score",
    "simplug-T010": "Oracle API sequence:\nmake_score_manager -> sp.disable -> sp.plugins_context -> sp.hooks.score -> sp.hooks.score",
}


LEGACY_API_SEQUENCE = """CAPIR-style recommended API sequence:
- For temporary plugin selection: make_score_manager -> sp.plugins_context -> sp.hooks.score
- For disabling a plugin: make_score_manager -> sp.disable or sp.get_plugin -> wrapper.disable -> sp.hooks.score

API descriptions:
- plugins_context(plugins): create a temporary plugin context.
- hooks.score(value): call the score hook.
- disable(*names): disable plugins.
- get_plugin(name): retrieve a plugin wrapper.
"""


GOLD_PAIR_RULES = """Relevant API Pair Rules:
1. sp.plugins_context -> sp.hooks.score
Relation: param-dependency
Constraint: To run a hook with only an existing plugin enabled, pass plugin names as strings, e.g. ["beta"]. Passing the plugin object beta means add/enable beta, not only-beta mode.
Usage pattern:
with sp.plugins_context(["beta"]):
    result = sp.hooks.score(value)

2. sp.disable -> sp.hooks.score
Relation: shared-receiver
Constraint: sp.disable("beta") changes the enabled state in the same Simplug manager; the following sp.hooks.score(value) should be called on the same sp.
Usage pattern:
sp.disable("beta")
result = sp.hooks.score(value)

3. sp.get_plugin -> wrapper.disable -> sp.hooks.score
Relation: return-flow
Constraint: sp.get_plugin("beta") returns the wrapper that should be used as the receiver of wrapper.disable(); the later hook call should use the same manager sp.
Usage pattern:
wrapper = sp.get_plugin("beta")
wrapper.disable()
result = sp.hooks.score(value)

4. sp.spec(result=...) -> sp.hooks.score
Relation: config-return-contract
Constraint: The hook's result mode decides the RETURN SHAPE of sp.hooks.score(value). make_first_score_manager / make_last_score_manager declare the score hook with result=FIRST / result=LAST, so sp.hooks.score(value) returns a SINGLE result (the first/last enabled plugin's, by registration order) -- NOT a list. Return it directly; do not wrap it in a list or index into it as if it were a list.
Usage pattern:
result = sp.hooks.score(value)   # a single ("name", number) tuple
return result

5. sp.disable / sp.plugins_context -> sp.hooks.score
Relation: state-lifecycle
Constraint: sp.disable(name) is PERSISTENT -- the plugin stays disabled after the call and across a later plugins_context. plugins_context temporarily changes the enabled set and, on exit, restores the state that held WHEN THE CONTEXT WAS ENTERED -- not "all plugins enabled". A plugin disabled before entering the context therefore remains disabled after the context exits.
Usage pattern:
sp.disable("beta")
with sp.plugins_context(["alpha"]):
    inside = sp.hooks.score(value)   # only alpha
after = sp.hooks.score(value)        # alpha and gamma (beta still disabled)
"""


METHODS = {
    "B0_direct": "",
    "B1_api_list": API_LIST,
    "B2_raw_api_docs": RAW_API_DOCS,
    "B3_oracle_api_sequence": None,
    "B3_api_sequence": LEGACY_API_SEQUENCE,
    "B4_gold_pair_rule": GOLD_PAIR_RULES,
}


def _split_pair_rules(block: str) -> dict[str, str]:
    """Split the GOLD_PAIR_RULES block into {relation: full_rule_text}.

    Each numbered rule carries a ``Relation: <name>`` line; B4 injects only the
    rule whose relation matches the task's pair_type (see PAIR_TYPE_TO_RELATION)
    instead of dumping all rules -- the all-rules dump leaks irrelevant usage
    patterns (e.g. plugins_context) into tasks that must not use them.
    """
    body = block.split("\n", 1)[1] if "\n" in block else block
    rules: dict[str, str] = {}
    for chunk in re.split(r"\n(?=\d+\.\s)", body):
        m = re.search(r"Relation:\s*(\S+)", chunk)
        if m:
            rules[m.group(1)] = chunk.strip()
    return rules


GOLD_PAIR_RULES_BY_RELATION = _split_pair_rules(GOLD_PAIR_RULES)
# task pair_type -> rule Relation tag (identity except where they differ)
PAIR_TYPE_TO_RELATION = {"lifecycle": "state-lifecycle"}


def gold_rule_for_task(task: dict) -> str:
    relation = PAIR_TYPE_TO_RELATION.get(task["pair_type"], task["pair_type"])
    rule = GOLD_PAIR_RULES_BY_RELATION.get(relation)
    if rule is None:
        raise KeyError(
            f"no gold pair rule for pair_type {task['pair_type']!r} "
            f"(relation {relation!r}); known: {sorted(GOLD_PAIR_RULES_BY_RELATION)}"
        )
    return "Relevant API Pair Rule:\n" + rule


def method_payload(task: dict, method: str) -> str:
    if method == "B3_oracle_api_sequence":
        return ORACLE_API_SEQUENCES[task["task_id"]]
    if method == "B4_gold_pair_rule":
        # B4 = B1's API knowledge PLUS this task's pair rule (strict superset of
        # B1, so B4-B1 isolates the pair rule's marginal value); only the
        # relevant rule is added, avoiding cross-task pattern contamination.
        return API_LIST + "\n\n" + gold_rule_for_task(task)
    payload = METHODS.get(method)
    if payload is None:
        raise KeyError(f"Unknown method: {method}")
    return payload


def build_prompt(task: dict, method_payload: str) -> str:
    helper = task.get("helper", "sp, alpha, beta, gamma = make_score_manager()")
    helper_func = helper.split("=", 1)[1].split("(", 1)[0].strip()
    return f"""You are writing Python code using the simplug library.
Return only Python code. Do not include Markdown fences. Do not explain.

Assume this helper already exists and is correct:
{helper}

Task:
{task["task"]}

{method_payload}

Requirements:
- Define only the requested function.
- Do not define {helper_func}.
- Do not define plugin classes.
- Use the existing variables returned by {helper_func}.
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
    start = min([i for i in [text.find("def "), text.find("from "), text.find("import ")] if i >= 0], default=0)
    return text[start:].strip()


def attr_chain(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = attr_chain(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


class SimplugChecker(ast.NodeVisitor):
    def __init__(self) -> None:
        self.plugins_context_args: list[ast.AST] = []
        self.disable_args: list[tuple[str, list[ast.AST]]] = []
        self.get_plugin_assigns: dict[str, str] = {}
        # Tracks variables bound to get_plugin() calls whose arg was NOT a string literal,
        # so check_task can emit "wrong parameter semantics" instead of "missing call".
        self.get_plugin_bad_arg_vars: set[str] = set()
        self.wrapper_disable_vars: set[str] = set()
        self.hook_receivers: list[str] = []

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and attr_chain(ctx.func) and attr_chain(ctx.func).endswith(".plugins_context"):
                if ctx.args:
                    self.plugins_context_args.append(ctx.args[0])
                for keyword in ctx.keywords:
                    if keyword.arg == "plugins":
                        self.plugins_context_args.append(keyword.value)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call) and attr_chain(node.value.func) and attr_chain(node.value.func).endswith(".get_plugin"):
            if node.value.args:
                arg = node.value.args[0]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.get_plugin_assigns[target.id] = arg.value
                else:
                    # get_plugin called with a non-string arg (e.g. the plugin object variable)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.get_plugin_bad_arg_vars.add(target.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        chain = attr_chain(node.func)
        if chain:
            if chain.endswith(".hooks.score"):
                self.hook_receivers.append(chain.rsplit(".hooks.score", 1)[0])
            if chain.endswith(".disable"):
                receiver = chain.rsplit(".disable", 1)[0]
                self.disable_args.append((receiver, list(node.args)))
                if receiver in self.get_plugin_assigns:
                    self.wrapper_disable_vars.add(receiver)
        self.generic_visit(node)


def list_string_values(node: ast.AST) -> set[str]:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        values = set()
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                values.add(elt.value.lstrip("+-"))
        return values
    return set()


def has_name_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(isinstance(elt, ast.Name) for elt in node.elts)
    return isinstance(node, ast.Name)


def check_task(code: str, task: dict) -> dict:
    if not code.strip():
        return {
            "syntax_valid": False,
            "pair_pass": False,
            "violations": ["empty_generation"],
            "error_types": ["empty_generation"],
            "details": "model returned no extractable code",
        }

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return {
            "syntax_valid": False,
            "pair_pass": False,
            "violations": ["syntax_error"],
            "error_types": ["syntax_error"],
            "details": str(e),
        }

    c = SimplugChecker()
    c.visit(tree)
    violations: list[str] = []
    error_types: list[str] = []

    if "expect_context_names" in task:
        expected = set(task["expect_context_names"])
        if not c.plugins_context_args:
            violations.append("missing sp.plugins_context")
            error_types.append("missing API call")
        else:
            ok = any(list_string_values(arg) == expected for arg in c.plugins_context_args)
            if not ok:
                violations.append(f"plugins_context should receive plugin name strings {sorted(expected)}")
                error_types.append("wrong parameter semantics")
            if any(has_name_value(arg) for arg in c.plugins_context_args):
                violations.append("plugins_context receives plugin object variable instead of name string")
                error_types.append("wrong parameter semantics")
    if task.get("expect_two_hook_calls"):
        if len(c.hook_receivers) < 2:
            violations.append("expected hook call inside and after context")
            error_types.append("missing API call")

    expected_disable_names = set()
    if "expect_disable_name" in task:
        expected_disable_names.add(task["expect_disable_name"])
    if "expect_disable_names" in task:
        expected_disable_names |= set(task["expect_disable_names"])
    if expected_disable_names:
        # For tasks that require sp.disable(...), using plugins_context as a substitute is wrong
        # even if the model also happens to include a correct sp.disable() call elsewhere.
        if c.plugins_context_args:
            violations.append(
                "unexpected sp.plugins_context in a disable-by-name task; use sp.disable instead"
            )
            error_types.append("wrong API pattern")

        any_sp_disable = any(receiver == "sp" for receiver, _ in c.disable_args)
        seen = set()
        object_arg = False
        for receiver, args in c.disable_args:
            # sp.disable("beta") style only. wrapper.disable() is handled separately.
            if receiver == "sp":
                for arg in args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        seen.add(arg.value)
                    if isinstance(arg, ast.Name):
                        object_arg = True
        if not any_sp_disable:
            # The call is entirely absent -- distinct from "called but with wrong args".
            violations.append("missing sp.disable call")
            error_types.append("missing API call")
        elif seen != expected_disable_names:
            violations.append(f"sp.disable should receive plugin name strings {sorted(expected_disable_names)}")
            error_types.append("wrong parameter semantics")
        if object_arg:
            violations.append("sp.disable receives plugin object variable instead of name string")
            error_types.append("wrong parameter semantics")

    if "expect_get_plugin_wrapper" in task:
        expected = task["expect_get_plugin_wrapper"]
        wrapper_vars = {var for var, name in c.get_plugin_assigns.items() if name == expected}
        bad_arg_vars = c.get_plugin_bad_arg_vars
        if not wrapper_vars and not bad_arg_vars:
            violations.append(f"missing sp.get_plugin('{expected}') assignment")
            error_types.append("broken data flow")
        elif bad_arg_vars and not wrapper_vars:
            # get_plugin was called but with a non-string arg (e.g. the plugin object variable).
            violations.append(
                f"sp.get_plugin called with non-string argument; pass the plugin name string '{expected}'"
            )
            error_types.append("wrong parameter semantics")
        elif not (wrapper_vars & c.wrapper_disable_vars):
            violations.append("get_plugin return value is not used as receiver of wrapper.disable()")
            error_types.append("broken data flow")

    if not c.hook_receivers:
        violations.append("missing sp.hooks.score call")
        error_types.append("missing API call")

    return {
        "syntax_valid": True,
        "pair_pass": not violations,
        "violations": sorted(set(violations)),
        "error_types": sorted(set(error_types)),
        "details": json.dumps(
            {
                "plugins_context_args": [ast.unparse(a) for a in c.plugins_context_args],
                "disable_args": [(r, [ast.unparse(a) for a in args]) for r, args in c.disable_args],
                "get_plugin_assigns": c.get_plugin_assigns,
                "get_plugin_bad_arg_vars": sorted(c.get_plugin_bad_arg_vars),
                "wrapper_disable_vars": sorted(c.wrapper_disable_vars),
                "hook_receivers": c.hook_receivers,
            },
            ensure_ascii=False,
        ),
    }


def safe_name(value: str) -> str:
    return value.replace(":", "_").replace("/", "_").replace(",", "__")


def parse_csv_arg(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def summarize(rows: list[dict], models: list[str], methods: list[str]) -> dict:
    """Aggregate rows into per-(model, method) statistics.

    When multiple runs exist for the same (task, model, method), a task counts
    as pair_pass only when it passes on a majority of those runs (>=50%).
    """
    summary: dict[str, dict] = {}
    for model in models:
        summary[model] = {}
        for method in methods:
            method_rows = [r for r in rows if r["model"] == model and r["method"] == method]
            n_rows = len(method_rows)

            # Group by task to apply majority-vote across runs.
            by_task: dict[str, list[bool]] = {}
            for r in method_rows:
                by_task.setdefault(r["task_id"], []).append(str(r["pair_pass"]) == "True")
            n_tasks = len(by_task)

            pair_pass_tasks = sum(
                1 for passes in by_task.values() if sum(passes) / len(passes) >= 0.5
            )
            syntax_valid = sum(str(r["syntax_valid"]) == "True" for r in method_rows)
            runs_per_task = n_rows // n_tasks if n_tasks else 1
            summary[model][method] = {
                "n_tasks": n_tasks,
                "runs_per_task": runs_per_task,
                "total_rows": n_rows,
                "syntax_valid": syntax_valid,
                "static_validity": syntax_valid / n_rows if n_rows else 0,
                "pair_pass": pair_pass_tasks,
                "pair_violation_rate": 1 - pair_pass_tasks / n_tasks if n_tasks else 0,
            }
    return summary


def run(
    models: list[str] | None = None,
    methods: list[str] | None = None,
    task_ids: list[str] | None = None,
    result_dir: Path | None = None,
    temperature: float = 0.2,
    retries: int = 1,
    runs: int = 1,
) -> None:
    """Run inference + evaluation for all (model, task, method) combinations.

    Args:
        runs: Number of independent inference runs per (model, task, method).
              When runs > 1, majority-vote aggregation is used in the summary.
              Files are named with a ``_run{i}`` suffix for i >= 2.
    """
    models = models or [DEFAULT_MODEL]
    methods = methods or parse_csv_arg(DEFAULT_METHODS)
    tasks = [task for task in TASKS if not task_ids or task["task_id"] in task_ids]
    unknown_methods = [method for method in methods if method not in METHODS]
    if unknown_methods:
        raise ValueError(f"Unknown methods: {', '.join(unknown_methods)}")
    if not tasks:
        raise ValueError("No tasks selected")

    if result_dir is None:
        run_name = f"simplug_model_method_comparison__{safe_name(','.join(models))}"
        result_dir = Path(__file__).resolve().parent / "result" / run_name
    root = result_dir

    root.mkdir(parents=True, exist_ok=True)
    (root / "prompts").mkdir(exist_ok=True)
    (root / "generations").mkdir(exist_ok=True)

    config = {
        "models": models,
        "methods": methods,
        "tasks": [task["task_id"] for task in tasks],
        "task_meta": {
            task["task_id"]: {
                "pair_type": task.get("pair_type", ""),
                "difficulty": task.get("difficulty", ""),
            }
            for task in tasks
        },
        "temperature": temperature,
        "retries": retries,
        "runs": runs,
        "ollama_url": OLLAMA_URL,
    }
    (root / "run_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    rows = []
    for run_idx in range(runs):
        run_suffix = "" if runs == 1 else f"_run{run_idx + 1}"
        for model in models:
            model_dir = safe_name(model)
            for task in tasks:
                for method in methods:
                    payload = method_payload(task, method)
                    prompt = build_prompt(task, payload)
                    prompt_path = root / "prompts" / f"{model_dir}__{task['task_id']}__{method}.txt"
                    if run_idx == 0:
                        prompt_path.write_text(prompt, encoding="utf-8")
                    print(
                        f"[run {run_idx + 1}/{runs}] model={model} task={task['task_id']} method={method}...",
                        flush=True,
                    )
                    started = time.time()
                    try:
                        response = ""
                        for attempt in range(retries + 1):
                            response = call_ollama(prompt, model=model, temperature=temperature)
                            if response.strip() or attempt == retries:
                                break
                            print(
                                f"Empty response; retrying model={model} task={task['task_id']} method={method}...",
                                flush=True,
                            )
                            time.sleep(1)
                        elapsed = time.time() - started
                        code = extract_code(response)
                        check = check_task(code, task)
                    except Exception as e:
                        elapsed = time.time() - started
                        response = ""
                        code = ""
                        check = {
                            "syntax_valid": False,
                            "pair_pass": False,
                            "violations": ["ollama_or_script_error"],
                            "error_types": ["experiment_error"],
                            "details": repr(e),
                        }
                    gen_name = f"{model_dir}__{task['task_id']}__{method}{run_suffix}"
                    generation_path = root / "generations" / f"{gen_name}.py"
                    response_path = root / "generations" / f"{gen_name}.raw.txt"
                    generation_path.write_text(code, encoding="utf-8")
                    response_path.write_text(response, encoding="utf-8")
                    rows.append(
                        {
                            "run_idx": run_idx + 1,
                            "task_id": task["task_id"],
                            "pair_type": task.get("pair_type", ""),
                            "difficulty": task.get("difficulty", ""),
                            "method": method,
                            "model": model,
                            "elapsed_sec": f"{elapsed:.2f}",
                            "syntax_valid": check["syntax_valid"],
                            "pair_pass": check["pair_pass"],
                            "pair_violation": not check["pair_pass"],
                            "error_types": "; ".join(check["error_types"]),
                            "violations": "; ".join(check["violations"]),
                            "details": check["details"],
                            "prompt_path": str(prompt_path),
                            "generation_path": str(generation_path),
                        }
                    )

    with (root / "pair_violation_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, models=models, methods=methods)
    (root / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md = [
        "# PairCoder Simplug Model x Method Comparison",
        "",
        f"- Models: {', '.join(f'`{model}`' for model in models)}",
        f"- Methods: {', '.join(f'`{method}`' for method in methods)}",
        f"- Tasks: {len(tasks)} pair-critical simplug tasks",
        f"- Temperature: `{temperature}`",
        f"- Runs per condition: `{runs}` (pair_pass uses majority vote across runs)",
        "- Evaluation: AST-based checker for plugins_context parameter semantics, get_plugin return-flow, and disable -> hook call.",
        "",
        "| Model | Method | Tasks | Runs | Static validity | Pair pass | Pair violation rate |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for model in models:
        for method in methods:
            s = summary[model][method]
            md.append(
                f"| {model} | {method} | {s['n_tasks']} | {s['runs_per_task']} | {s['static_validity']:.2f} | {s['pair_pass']} | {s['pair_violation_rate']:.2f} |"
            )

    md.extend(["", "## Pair Violation Rate Matrix", ""])
    md.append("| Method | " + " | ".join(models) + " |")
    md.append("|---" + "|---:" * len(models) + "|")
    for method in methods:
        cells = [f"{summary[model][method]['pair_violation_rate']:.2f}" for model in models]
        md.append("| " + method + " | " + " | ".join(cells) + " |")

    md.extend(
        [
            "",
            "## Interpretation Guide",
            "",
            "- `B3_oracle_api_sequence` gives the correct API order but does not state pair constraints.",
            "- The problem-existence claim is supported when `B3_oracle_api_sequence` still has non-zero pair violations on a stronger model.",
            "- `B4_gold_pair_rule` is an oracle upper-bound condition, not the final automatic PairCoder system.",
        ]
    )
    (root / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote results to {root}")


def legacy_single_model_run() -> None:
    root = Path(__file__).resolve().parent / f"paircoder_step0_simplug_results__{safe_name(DEFAULT_MODEL)}"
    root.mkdir(parents=True, exist_ok=True)
    (root / "prompts").mkdir(exist_ok=True)
    (root / "generations").mkdir(exist_ok=True)
    rows = []
    for task in TASKS:
        for method in ["B1_api_list", "B3_api_sequence", "B4_gold_pair_rule"]:
            payload = method_payload(task, method)
            prompt = build_prompt(task, payload)
            prompt_path = root / "prompts" / f"{task['task_id']}__{method}.txt"
            prompt_path.write_text(prompt, encoding="utf-8")
            print(f"Running {task['task_id']} {method}...", flush=True)
            started = time.time()
            try:
                response = call_ollama(prompt, model=DEFAULT_MODEL, temperature=0.2)
                elapsed = time.time() - started
                code = extract_code(response)
                check = check_task(code, task)
            except Exception as e:
                elapsed = time.time() - started
                response = ""
                code = ""
                check = {
                    "syntax_valid": False,
                    "pair_pass": False,
                    "violations": ["ollama_or_script_error"],
                    "error_types": ["experiment_error"],
                    "details": repr(e),
                }
            generation_path = root / "generations" / f"{task['task_id']}__{method}.py"
            response_path = root / "generations" / f"{task['task_id']}__{method}.raw.txt"
            generation_path.write_text(code, encoding="utf-8")
            response_path.write_text(response, encoding="utf-8")
            rows.append(
                {
                    "task_id": task["task_id"],
                    "method": method,
                    "model": DEFAULT_MODEL,
                    "elapsed_sec": f"{elapsed:.2f}",
                    "syntax_valid": check["syntax_valid"],
                    "pair_pass": check["pair_pass"],
                    "pair_violation": not check["pair_pass"],
                    "error_types": "; ".join(check["error_types"]),
                    "violations": "; ".join(check["violations"]),
                    "details": check["details"],
                    "prompt_path": str(prompt_path),
                    "generation_path": str(generation_path),
                }
            )

    with (root / "pair_violation_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {}
    for method in ["B1_api_list", "B3_api_sequence", "B4_gold_pair_rule"]:
        method_rows = [r for r in rows if r["method"] == method]
        n = len(method_rows)
        pair_pass = sum(str(r["pair_pass"]) == "True" for r in method_rows)
        syntax_valid = sum(str(r["syntax_valid"]) == "True" for r in method_rows)
        summary[method] = {
            "n": n,
            "syntax_valid": syntax_valid,
            "static_validity": syntax_valid / n if n else 0,
            "pair_pass": pair_pass,
            "pair_violation_rate": 1 - pair_pass / n if n else 0,
        }
    (root / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md = [
        "# PairCoder Step 0 Simplug Pilot Results",
        "",
        f"- Model: `{DEFAULT_MODEL}`",
        "- Library: `simplug`",
        "- Tasks: 6 pair-critical tasks",
        "- Evaluation: AST-based checker for plugins_context parameter semantics, get_plugin return-flow, and disable -> hook call.",
        "",
        "| Method | n | Static validity | Pair pass | Pair violation rate |",
        "|---|---:|---:|---:|---:|",
    ]
    for method, s in summary.items():
        md.append(f"| {method} | {s['n']} | {s['static_validity']:.2f} | {s['pair_pass']} | {s['pair_violation_rate']:.2f} |")
    (root / "summary.md").write_text("\n".join(md), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote results to {root}")


def reeval(result_dir: Path) -> None:
    """Re-run check_task on already-generated .py files in result_dir.

    Useful for applying checker fixes to existing data without re-running inference.
    Reads the saved run_config.json to discover models/methods/tasks, then re-evaluates
    every generation file found, overwrites pair_violation_results.csv and summary.json.
    """
    config_path = result_dir / "run_config.json"
    if not config_path.exists():
        raise FileNotFoundError(f"No run_config.json found in {result_dir}")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    models: list[str] = config["models"]
    methods: list[str] = config["methods"]
    task_ids: list[str] = config["tasks"]
    runs: int = config.get("runs", 1)
    task_map = {t["task_id"]: t for t in TASKS}

    rows = []
    for run_idx in range(runs):
        run_suffix = "" if runs == 1 else f"_run{run_idx + 1}"
        for model in models:
            model_dir = safe_name(model)
            for task_id in task_ids:
                task = task_map[task_id]
                for method in methods:
                    gen_name = f"{model_dir}__{task_id}__{method}{run_suffix}"
                    generation_path = result_dir / "generations" / f"{gen_name}.py"
                    prompt_path = result_dir / "prompts" / f"{model_dir}__{task_id}__{method}.txt"
                    if not generation_path.exists():
                        print(f"WARNING: missing generation file {generation_path}", flush=True)
                        continue
                    code = generation_path.read_text(encoding="utf-8")
                    check = check_task(code, task)
                    rows.append(
                        {
                            "run_idx": run_idx + 1,
                            "task_id": task_id,
                            "method": method,
                            "model": model,
                            "elapsed_sec": "N/A",
                            "syntax_valid": check["syntax_valid"],
                            "pair_pass": check["pair_pass"],
                            "pair_violation": not check["pair_pass"],
                            "error_types": "; ".join(check["error_types"]),
                            "violations": "; ".join(check["violations"]),
                            "details": check["details"],
                            "prompt_path": str(prompt_path),
                            "generation_path": str(generation_path),
                        }
                    )
                    status = "PASS" if check["pair_pass"] else "FAIL"
                    print(f"[reeval run{run_idx+1}] {model} {task_id} {method}: {status}", flush=True)

    if not rows:
        print("No generation files found -- nothing to reeval.")
        return

    with (result_dir / "pair_violation_results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, models=models, methods=methods)
    (result_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Rewrote results in {result_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PairCoder simplug model x method comparison with Ollama.")
    parser.add_argument("--models", default=DEFAULT_MODELS, help="Comma-separated Ollama model names.")
    parser.add_argument("--methods", default=DEFAULT_METHODS, help="Comma-separated method names.")
    parser.add_argument("--tasks", default="", help="Optional comma-separated task ids for smoke tests.")
    parser.add_argument("--result-dir", default="", help="Optional output directory.")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--retries", type=int, default=1, help="Retries for empty Ollama responses.")
    parser.add_argument("--runs", type=int, default=1, help="Independent inference runs per condition; summary uses majority vote.")
    parser.add_argument("--reeval", action="store_true", help="Re-run the checker on saved generation files without new inference.")
    parser.add_argument("--legacy", action="store_true", help="Run the original single-model B1/B3/B4 pilot.")
    args = parser.parse_args()
    if args.legacy:
        legacy_single_model_run()
        return
    result_dir = Path(args.result_dir).expanduser().resolve() if args.result_dir else None
    if args.reeval:
        if not result_dir:
            parser.error("--reeval requires --result-dir")
        reeval(result_dir)
        return
    run(
        models=parse_csv_arg(args.models),
        methods=parse_csv_arg(args.methods),
        task_ids=parse_csv_arg(args.tasks) if args.tasks else None,
        result_dir=result_dir,
        temperature=args.temperature,
        retries=args.retries,
        runs=args.runs,
    )


if __name__ == "__main__":
    main()
