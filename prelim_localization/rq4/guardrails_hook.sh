#!/usr/bin/env bash
# SessionStart hook: 把 RQ4 契约的 §0(锁定决策) + §7(DO/DON'T) 注入每个新会话，防跑偏。
# stdout 会被 Claude Code 作为 SessionStart additionalContext 注入。
SPEC="/Users/zt25/coding/localization_line/prelim_localization/rq4/RQ4_SPEC.md"
[ -f "$SPEC" ] || exit 0
echo "==== RQ4 防跑偏护栏（自动注入自 RQ4_SPEC.md，契约为唯一事实源）===="
awk '/^## 0\./{f=1} /^## 1\./{f=0} f' "$SPEC"
echo ""
awk '/^## 7\./{f=1} /^## 8\./{f=0} f' "$SPEC"
echo ""
echo "（运行期只读 rq4/frozen_subsets.json；一切实验经 rq4/run_all.py；改 §0/§1/§2 须先写 changelog）"
