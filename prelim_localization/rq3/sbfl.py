#!/usr/bin/env python3
import os as _os, sys as _sys; _d=_os.path.dirname(_os.path.abspath(__file__)); _sys.path[:0]=[_d,_os.path.dirname(_d)]; _os.chdir(_os.path.dirname(_d))
"""SBFL (Spectrum-Based Fault Localization) for crash-bug line ranking — RQ3-E3.
The KEY differential signal: lines covered by the FAILING test(s) but NOT by the PASSING test(s) are
suspicious (they are on the crash-specific path, separated from import-chain noise covered by all tests).

Coverage granularity note: the project's cov cache stores the UNION of executed lines per instance
(not per-test). So we use the BINARY-GROUP Ochiai (one failing group, one passing group):
  ef = 1 if line in failing-cov else 0 ;  ep = 1 if line in passing-cov else 0
  ochiai = ef / sqrt((ef+nf)*(ef+ep))  with nf=1-ef (single failing group), giving a {fail-only,both,
  pass-only,neither} ranking. Proper per-test Ochiai needs per-test coverage (a richer P1 collection).

Usage in the ranker: restrict candidates to failing-cov (the coverage-FILTER, RQ3-E1 +14pp), then
order by SBFL tier (fail-only > both), breaking ties by the static def-use score. Ready to plug into
region_loc once passing-test coverage is collected (egl_cov_cache_pass.json)."""
import math

def ochiai_binary(line, failing, passing):
    """Binary-group Ochiai suspiciousness for one line. failing/passing = sets of executed lines."""
    ef = 1 if line in failing else 0
    ep = 1 if line in passing else 0
    nf = 1 - ef                                  # 1 failing group
    denom = math.sqrt((ef + nf) * (ef + ep)) if (ef + ep) > 0 else 0.0
    return (ef / denom) if denom > 0 else 0.0

def sbfl_rank(candidate_lines, failing, passing, static_scores=None):
    """Rank candidate_lines by SBFL (fail-specific first), tie-broken by static def-use score then line#.
    candidate_lines: iterable of line numbers (typically the file's scored lines).
    failing/passing: sets of executed line numbers (union over the resp. test group).
    Returns lines sorted most-suspicious-first."""
    static_scores = static_scores or {}
    def key(l):
        susp = ochiai_binary(l, failing, passing)          # 1.0 fail-only, ~0.707 both, 0 otherwise
        return (-susp, -static_scores.get(l, 0.0), l)
    return sorted(candidate_lines, key=key)

def sbfl_filter_rank(candidate_lines, failing, passing, static_scores=None):
    """RQ3-E3 main arm: coverage-FILTER (keep only failing-covered lines) THEN SBFL order.
    This composes the +14pp filter (RQ3-E1) with the differential SBFL signal."""
    cand = [l for l in candidate_lines if l in failing]    # the filter (on-path: gold survives)
    return sbfl_rank(cand, failing, passing, static_scores)

if __name__ == "__main__":
    # tiny self-test (no data needed)
    failing = {10, 11, 12, 20}; passing = {11, 12, 30}     # 10,20 = fail-only(suspicious); 11,12 = both
    static = {10: 0.1, 11: 0.9, 12: 0.2, 20: 0.05, 30: 0.5}
    r = sbfl_filter_rank([10, 11, 12, 20, 30], failing, passing, static)
    assert r[0] in (10, 20) and 30 not in r, r              # fail-only ranks first; 30 (pass-only) filtered out
    print("sbfl.py self-test OK:", r)
