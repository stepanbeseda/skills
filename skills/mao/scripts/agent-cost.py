#!/usr/bin/env python3
"""Token use and estimated cost of a Claude Code session and its subagents.

Reads the session transcript and the transcripts of every subagent it started,
counts each API call once, prices the usage with the table below and prints a
table grouped the way you ask (per agent, role, model, phase, PR, ...). Use it
to measure a MAO run per PR and phase, and to compare an experiment with its
baseline.

Where the transcripts are (Claude Code):
  ~/.claude/projects/<project-slug>/<session-id>.jsonl            the orchestrator
  ~/.claude/projects/<project-slug>/<session-id>/subagents/agent-*.jsonl (+ .meta.json)

Usage:
  agent-cost.py SESSION.jsonl [SESSION.jsonl ...] [options]
  agent-cost.py ~/.claude/projects/<project-slug>/<session-id>.jsonl --by pr,phase
  agent-cost.py SESSION.jsonl --by phase --match '^PR-07 ' --since 2026-01-01T00:00
  agent-cost.py SESSION.jsonl --by agent --top 20

Options:
  --by KEYS        comma-separated grouping: agent, role, model, phase, pr, desc, day
                   (default: role)
  --match REGEX    only agents whose description matches (the orchestrator's
                   description is "orchestrator")
  --since/--until  ISO timestamps (UTC); only API calls in that window count
  --prices FILE    JSON {"<model substring>": [input, output, cache_read,
                   cache_write_5m, cache_write_1h], ...} in $ per million tokens;
                   replaces the table below
  --pr-regex REGEX how to find the PR in a description (default: PR-?\\s?(\\d+))
  --no-orchestrator  leave the main session out
  --top N          print only the N largest groups
  --json           print one JSON object per agent instead of the table

Counting rules:
  - One API call can appear on several transcript lines; it is counted once
    (by requestId, keeping the line with the largest output_tokens).
  - Context per step = input + cache write + cache read of that call.
  - Wall = time from the first to the last call, without gaps over one hour.
    Idle = the sum of gaps over five minutes (waiting on a job, a user or a
    resume). Rewrite $ = the extra cost of re-writing the cache after such a
    gap (the 5-minute cache expired), counted as (write - read price) times the
    tokens written beyond the context growth of that step.
  - Phase comes from the agent's description (see PHASES). MAO prompts name
    agents "PR-NN <phase> [part K]", which these patterns match.

All dollar amounts are estimates from the price table. Check the current
prices of your provider and edit PRICES (or pass --prices) before you quote
a number; ratios between phases and between runs do not depend on the level.
"""
import argparse
import collections
import datetime as dt
import glob
import json
import os
import re
import sys

# $ per million tokens: input, output, cache read, cache write (5 min), cache write (1 h).
# Example list prices; edit them. The key is matched as a substring of the model id.
PRICES = {
    "opus": [5.00, 25.00, 0.50, 6.25, 10.00],
    "sonnet": [3.00, 15.00, 0.30, 3.75, 6.00],
    "haiku": [1.00, 5.00, 0.10, 1.25, 2.00],
}

# (phase, pattern on the lower-cased description); the first match wins.
PHASES = [
    ("pr-body", r"pr body"),
    ("preview", r"preview"),
    ("gate", r"\bgate\b|check run|final check"),
    ("rebase", r"rebase|conflict"),
    ("spec-check", r"spec check|re-?check"),
    ("spec-fix", r"spec fix|addendum|brief fix"),
    ("delta-review", r"delta review|review (round |r)?[2-9]\b"),
    ("review-r1", r"review"),
    ("fix-round", r"fix round|\bfix \d"),
    ("inventory", r"inventory"),
    ("design", r"design|spec\b|questions|brief"),
    ("implementation", r"implement|impl\b|\bpart \d"),
    ("docs", r"docs|delivered|plan edit"),
    ("setup", r"setup"),
]

IDLE_GAP = 300      # seconds: a longer gap expires the 5-minute cache
RESUME_GAP = 3600   # seconds: longer gaps are not counted as wall time


def ts(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def price_for(model, prices):
    model = (model or "").lower()
    for key, row in prices.items():
        if key in model:
            return row
    return None


def phase_of(desc):
    d = (desc or "").lower()
    if d == "orchestrator":
        return "orchestrator"
    for name, pattern in PHASES:
        if re.search(pattern, d):
            return name
    return "other"


def read_calls(path, since, until):
    """Return (calls, tool_use_count) of one transcript, one entry per API call."""
    calls = {}
    tool_ids = set()
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") != "assistant":
                continue
            msg = rec.get("message") or {}
            model = msg.get("model") or ""
            if not model or "synthetic" in model:
                continue
            stamp = rec.get("timestamp")
            if stamp and ((since and stamp < since) or (until and stamp > until)):
                continue
            for block in msg.get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_ids.add(block.get("id"))
            usage = msg.get("usage") or {}
            rid = rec.get("requestId") or msg.get("id") or id(rec)
            old = calls.get(rid)
            if old is not None and usage.get("output_tokens", 0) < old["out"]:
                continue
            cache = usage.get("cache_creation") or {}
            calls[rid] = {
                "ts": old["ts"] if old else stamp,
                "model": model,
                "inp": usage.get("input_tokens", 0),
                "cw": usage.get("cache_creation_input_tokens", 0),
                "cw1h": cache.get("ephemeral_1h_input_tokens", 0),
                "cr": usage.get("cache_read_input_tokens", 0),
                "out": usage.get("output_tokens", 0),
            }
    ordered = sorted(calls.values(), key=lambda c: c["ts"] or "")
    return ordered, len(tool_ids)


def agent_row(agent_id, meta, calls, tools, prices, pr_regex):
    desc = meta.get("description") or ""
    role = (meta.get("agentType") or "").split(":")[-1]
    if role.startswith("mao-"):
        role = role[4:]
    pr = re.search(pr_regex, desc)
    row = collections.Counter()
    models = collections.Counter()
    prev = None
    max_ctx = 0
    for call in calls:
        p = price_for(call["model"], prices) or [0, 0, 0, 0, 0]
        cw5 = call["cw"] - call["cw1h"]
        cost = (call["inp"] * p[0] + call["out"] * p[1] + call["cr"] * p[2]
                + cw5 * p[3] + call["cw1h"] * p[4]) / 1e6
        ctx = call["inp"] + call["cw"] + call["cr"]
        max_ctx = max(max_ctx, ctx)
        models[call["model"]] += cost
        row.update(calls=1, inp=call["inp"], cw=call["cw"], cr=call["cr"], out=call["out"],
                   cost=cost, ctx=ctx)
        if prev and call["ts"] and prev["ts"]:
            gap = (ts(call["ts"]) - ts(prev["ts"])).total_seconds()
            if gap <= RESUME_GAP:
                row["wall"] += gap
            if gap > IDLE_GAP:
                row["idle"] += gap
                row["waits"] += 1
                extra = max(0, cw5 - max(0, ctx - prev["ctx"]))
                row["rewrite"] += extra * (p[3] - p[2]) / 1e6
        prev = {"ts": call["ts"], "ctx": ctx}
    model = models.most_common(1)[0][0] if models else ""
    day = (calls[0]["ts"] or "")[:10] if calls else ""
    return {
        "agent": agent_id, "desc": desc, "role": role or "orchestrator",
        "model": model, "phase": phase_of(desc), "pr": pr.group(1) if pr else "-", "day": day,
        "tools": tools, "max_ctx": max_ctx, **row,
    }


def load_session(path, args, prices):
    rows = []
    base = path[:-len(".jsonl")] if path.endswith(".jsonl") else path
    if not args.no_orchestrator and os.path.isfile(base + ".jsonl"):
        calls, tools = read_calls(base + ".jsonl", args.since, args.until)
        if calls:
            rows.append(agent_row("orchestrator", {"description": "orchestrator"}, calls, tools,
                                  prices, args.pr_regex))
    for sub in sorted(glob.glob(os.path.join(base, "subagents", "agent-*.jsonl"))):
        meta_path = sub[:-len(".jsonl")] + ".meta.json"
        meta = {}
        if os.path.isfile(meta_path):
            with open(meta_path, encoding="utf-8") as fh:
                meta = json.load(fh)
        calls, tools = read_calls(sub, args.since, args.until)
        if calls:
            agent_id = os.path.basename(sub)[len("agent-"):-len(".jsonl")]
            rows.append(agent_row(agent_id, meta, calls, tools, prices, args.pr_regex))
    return rows


def fmt_m(n):
    return f"{n / 1e6:.2f}"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("sessions", nargs="+")
    ap.add_argument("--by", default="role")
    ap.add_argument("--match")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--prices")
    ap.add_argument("--pr-regex", default=r"PR-?\s?(\d+)")
    ap.add_argument("--no-orchestrator", action="store_true")
    ap.add_argument("--top", type=int)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    prices = PRICES
    if args.prices:
        with open(args.prices, encoding="utf-8") as fh:
            prices = json.load(fh)
    rows = []
    for session in args.sessions:
        rows += load_session(os.path.expanduser(session), args, prices)
    if args.match:
        rows = [r for r in rows if re.search(args.match, r["desc"])]
    if not rows:
        print("no API calls found", file=sys.stderr)
        return 1
    if args.json:
        for r in rows:
            print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}))
        return 0

    keys = [k.strip() for k in args.by.split(",") if k.strip()]
    for k in keys:
        if k not in ("agent", "role", "model", "phase", "pr", "desc", "day"):
            ap.error(f"unknown --by key: {k}")
    groups = collections.defaultdict(collections.Counter)
    maxima = collections.defaultdict(int)
    for r in rows:
        key = " / ".join(str(r[k]) for k in keys)
        g = groups[key]
        g.update({f: r.get(f, 0) for f in ("calls", "tools", "inp", "cw", "cr", "out", "cost",
                                           "ctx", "wall", "idle", "waits", "rewrite")})
        g["agents"] += 1
        maxima[key] = max(maxima[key], r["max_ctx"])
    total = sum(g["cost"] for g in groups.values()) or 1.0
    order = sorted(groups, key=lambda k: -groups[k]["cost"])
    if args.top:
        order = order[:args.top]

    head = (f"{'/'.join(keys):40.40} {'agents':>6} {'calls':>6} {'tools':>6} {'tools/ag':>8} "
            f"{'in M':>6} {'cw M':>7} {'cr M':>8} {'out M':>6} {'$':>9} {'%':>6} "
            f"{'ctx avg k':>9} {'ctx max k':>9} {'wall h':>7} {'idle h':>7} {'rewrite $':>9}")
    print(head)
    print("-" * len(head))
    for key in order:
        g = groups[key]
        print(f"{key:40.40} {g['agents']:>6} {g['calls']:>6} {g['tools']:>6} "
              f"{g['tools'] / g['agents']:>8.0f} {fmt_m(g['inp']):>6} {fmt_m(g['cw']):>7} "
              f"{fmt_m(g['cr']):>8} {fmt_m(g['out']):>6} {g['cost']:>9.2f} "
              f"{100 * g['cost'] / total:>5.1f}% {g['ctx'] / max(g['calls'], 1) / 1e3:>9.0f} "
              f"{maxima[key] / 1e3:>9.0f} {g['wall'] / 3600:>7.1f} {g['idle'] / 3600:>7.1f} "
              f"{g['rewrite']:>9.2f}")
    all_ = collections.Counter()
    for g in groups.values():
        all_.update(g)
    print("-" * len(head))
    print(f"{'total':40} {all_['agents']:>6} {all_['calls']:>6} {all_['tools']:>6} {'':>8} "
          f"{fmt_m(all_['inp']):>6} {fmt_m(all_['cw']):>7} {fmt_m(all_['cr']):>8} "
          f"{fmt_m(all_['out']):>6} {all_['cost']:>9.2f} {'100.0%':>6}")
    print("Estimated $ from the price table in this script (or --prices); check current prices.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
