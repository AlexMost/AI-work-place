#!/usr/bin/env python3
"""Unattended pool-page updater for GitHub Actions — the automatic counterpart of
`pool_spy.py`.

Gate: one full `pool_spy.collect` per run produces a signature of the entire visible pool
state — per match (status / score / started) and per (match, member) the visible pick and
points. The expensive part (build_site writing every match page + the gh-pages deploy)
runs only when that signature moved since the last deploy (`.state.json`).

Why hash the *full* collected state rather than a cheap sample of a few members: the pool
has only a handful of members, so the per-member fetch a sample would skip is nearly free,
while sampling a fixed subset is blind to changes that land on matches those members did
not drive — exactly the "scores appeared mid-match but the gate stayed UNCHANGED" failure.
The events that must trigger a redeploy are global but land per match/member: other
members' picks revealed after kickoff (a pick goes from absent → present in `preds`),
points (re)computed, and the final score landing. Hashing the whole collected state catches
all of them with no blind spot, and the collect we hash is the same one we render from —
no second fetch.

Writes `changed=true|false` to --github-output ($GITHUB_OUTPUT) so the workflow can gate
the deploy. On a stale token the underlying api_get exits non-zero, failing the run — the
signal to refresh the POOL_API_TOKEN secret. Pure stdlib; reuses pool_spy.py alongside it.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import pool_spy


def _hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def state_signature(matches, preds):
    """Hash of the full visible pool state — moves on any change that should redeploy.

    `preds[mid][uid] = {"goals": (h, a), "points": int|None}` only holds *visible* picks,
    so a reveal grows the per-match dict; `matches` carries status/score/started.
    """
    payload = {
        "m": {mid: [m.get("status"), m.get("homeGoals"), m.get("awayGoals"),
                    pool_spy.has_started(m)]
              for mid, m in sorted(matches.items())},
        "p": {mid: {uid: [e["goals"][0], e["goals"][1], e["points"]]
                    for uid, e in sorted(users.items())}
              for mid, users in sorted(preds.items())},
    }
    return _hash(payload)


def read_prev_state(path):
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f) or {}
    except (json.JSONDecodeError, OSError):
        return {}


def write_output(github_output, changed):
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as f:
        f.write(f"changed={'true' if changed else 'false'}\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--token", help="Bearer token (else POOL_API_TOKEN env / .env)")
    ap.add_argument("--pool-id", default=None,
                    help=f"pool id (default {pool_spy.DEFAULT_POOL_ID})")
    ap.add_argument("--out", default=pool_spy.DEFAULT_OUT,
                    help="output dir (default <footbal>/pool)")
    ap.add_argument("--prev-state", help="previously deployed .state.json (for the gate)")
    ap.add_argument("--github-output", help="append changed=true|false here ($GITHUB_OUTPUT)")
    ap.add_argument("--force", action="store_true",
                    help="skip the gate and always do a full render")
    args = ap.parse_args()

    pool_spy.load_dotenv()
    pool_id = args.pool_id or os.environ.get("POOL_ID") or pool_spy.DEFAULT_POOL_ID
    token = args.token or os.environ.get("POOL_API_TOKEN")
    if not token:
        sys.exit("error: no token. Set POOL_API_TOKEN (env / .env) or pass --token.")

    prev = read_prev_state(args.prev_state)
    participants, matches, preds, phases = pool_spy.collect(token, pool_id)
    sig = state_signature(matches, preds)

    if not args.force and sig == prev.get("probe_signature"):
        write_output(args.github_output, False)
        print(f"UNCHANGED · matches: {len(matches)} · sig {sig[:12]}")
        return

    rendered = pool_spy.build_site(participants, matches, preds, args.out,
                                   show_all=False, only_match=None, phases=phases)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, ".state.json"), "w", encoding="utf-8") as f:
        json.dump({"probe_signature": sig,
                   "generated_at": datetime.now().isoformat(timespec="seconds")},
                  f, ensure_ascii=False, indent=2)

    write_output(args.github_output, True)
    print(f"CHANGED · participants: {len(participants)} · matches rendered: {len(rendered)}"
          f" · sig {sig[:12]}")


if __name__ == "__main__":
    main()
