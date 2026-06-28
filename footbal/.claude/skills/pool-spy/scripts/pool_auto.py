#!/usr/bin/env python3
"""Unattended pool-page updater for GitHub Actions — the automatic counterpart of
`pool_spy.py`.

The gate has two tiers so it is both cheap when idle and correct when matches are in play:

  * A cheap pre-check (one participant's predictions across phases, ~10 API calls) reads
    match metadata. If NO match has started in the last 24h AND that metadata is identical
    to the last deploy, the run skips — nothing can have changed.
  * Otherwise it does the full fetch + render (`pool_spy.collect` / `build_site`, reusing
    `pool_spy.py`) and compares a FULL signature that includes every member's predictions
    and points. It deploys only when that signature actually moved.

The full signature matters because the cheap metadata cannot see what does change during a
match: other members' picks are revealed only after kickoff, and points are (re)computed
later — both are invisible from your own predictions alone.

It writes `changed=true|false` to the file given by --github-output (GitHub Actions reads
$GITHUB_OUTPUT) so the workflow can gate the deploy step. On a stale token the underlying
api_get exits non-zero, which fails the run — the intended signal to refresh the
POOL_API_TOKEN secret. Pure stdlib; reuses pool_spy.py from the same directory.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime

import pool_spy

ACTIVE_WINDOW_S = 24 * 3600   # a match started within this window may still be settling


def _hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def cheap_match_meta(token, pool_id):
    """Match metadata only, fetched cheaply (one participant across phases, ~10 calls).

    Match metadata is identical regardless of whose predictions we read, so a single
    participant is enough to learn each match's status/score/kickoff.
    """
    phase_objs = pool_spy.fetch_phases(token)
    phase_ids = [ph.get("id") for ph in phase_objs
                 if ph.get("id") and (ph.get("matchCount") or 0) > 0] or [None]
    participants = pool_spy.fetch_participants(token, pool_id)
    matches = {}
    if participants:
        uid = participants[0]["id"]
        for phase_id in phase_ids:
            for entry in pool_spy.fetch_user_predictions(token, uid, pool_id, phase_id):
                m = entry.get("match") or {}
                mid = m.get("matchId")
                if mid:
                    matches[mid] = m
    return matches


def meta_signature(matches):
    payload = {mid: [m.get("status"), m.get("homeGoals"), m.get("awayGoals"),
                     pool_spy.has_started(m)]
               for mid, m in matches.items()}
    return _hash(payload)


def has_active_match(matches):
    now = time.time()
    for m in matches.values():
        ts = m.get("timeStamp")
        if ts and ts <= now and (now - ts) < ACTIVE_WINDOW_S:
            return True
    return False


def full_signature(matches, preds):
    """Everything that affects the rendered pages: match state + every member's pick and
    points. Excludes volatile fields (timestamps) so a no-op run hashes identically."""
    payload = {}
    for mid, m in matches.items():
        payload[mid] = {
            "s": m.get("status"),
            "h": m.get("homeGoals"),
            "a": m.get("awayGoals"),
            "st": pool_spy.has_started(m),
            "p": {uid: [v.get("goals"), v.get("points")]
                  for uid, v in preds.get(mid, {}).items()},
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

    meta = cheap_match_meta(token, pool_id)
    meta_sig = meta_signature(meta)
    active = has_active_match(meta)

    # cheap skip: nothing in play and match metadata identical to the last deploy
    if not args.force and not active and meta_sig == prev.get("meta_signature"):
        write_output(args.github_output, False)
        print(f"UNCHANGED (idle) · matches: {len(meta)} · no match started in the last 24h")
        return

    participants, matches, preds, phases = pool_spy.collect(token, pool_id)
    full_sig = full_signature(matches, preds)

    if not args.force and full_sig == prev.get("full_signature"):
        write_output(args.github_output, False)
        print(f"UNCHANGED · participants: {len(participants)} · signature {full_sig[:12]}")
        return

    rendered = pool_spy.build_site(participants, matches, preds, args.out,
                                   show_all=False, only_match=None, phases=phases)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, ".state.json"), "w", encoding="utf-8") as f:
        json.dump({"full_signature": full_sig, "meta_signature": meta_sig,
                   "generated_at": datetime.now().isoformat(timespec="seconds")},
                  f, ensure_ascii=False, indent=2)

    write_output(args.github_output, True)
    print(f"CHANGED · participants: {len(participants)} · matches rendered: {len(rendered)}"
          f" · signature {full_sig[:12]}")


if __name__ == "__main__":
    main()
