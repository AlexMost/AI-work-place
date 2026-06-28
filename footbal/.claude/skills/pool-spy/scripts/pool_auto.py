#!/usr/bin/env python3
"""Unattended pool-page updater for GitHub Actions — the automatic counterpart of
`pool_spy.py`.

Each run does a cheap snapshot of match state (one participant's predictions across
phases, ~10 API calls) and compares its signature to the previously deployed state. Only
when something changed (a match kicked off, a live/final score moved) does it do the full
fetch + render that `pool_spy.py` does. This keeps the API load and the gh-pages commit
noise down to actual changes.

It writes `changed=true|false` to the file given by --github-output (GitHub Actions reads
$GITHUB_OUTPUT) so the workflow can gate the deploy step. On a stale token the underlying
api_get exits non-zero, which fails the run — that is the intended signal to refresh the
POOL_API_TOKEN secret. Pure stdlib; reuses pool_spy.py from the same directory.
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime

import pool_spy


def cheap_snapshot(token, pool_id):
    """Match state (status + score + started) for every match, fetched cheaply.

    Match metadata is identical regardless of whose predictions we read, so we pull a
    single participant across every phase instead of all members — ~10 calls vs ~240.
    """
    phase_objs = pool_spy.fetch_phases(token)
    phase_ids = [ph.get("id") for ph in phase_objs
                 if ph.get("id") and (ph.get("matchCount") or 0) > 0] or [None]
    participants = pool_spy.fetch_participants(token, pool_id)
    if not participants:
        return {}
    uid = participants[0]["id"]
    snapshot = {}
    for phase_id in phase_ids:
        for entry in pool_spy.fetch_user_predictions(token, uid, pool_id, phase_id):
            m = entry.get("match") or {}
            mid = m.get("matchId")
            if not mid:
                continue
            snapshot[mid] = [
                m.get("status"),
                m.get("homeGoals"),
                m.get("awayGoals"),
                pool_spy.has_started(m),
            ]
    return snapshot


def signature(snapshot):
    payload = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_prev_signature(path):
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return (json.load(f) or {}).get("signature")
    except (json.JSONDecodeError, OSError):
        return None


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

    snapshot = cheap_snapshot(token, pool_id)
    sig = signature(snapshot)
    prev_sig = read_prev_signature(args.prev_state)

    if not args.force and sig == prev_sig:
        write_output(args.github_output, False)
        print(f"UNCHANGED · matches: {len(snapshot)} · signature {sig[:12]}")
        return

    participants, matches, preds, phases = pool_spy.collect(token, pool_id)
    rendered = pool_spy.build_site(participants, matches, preds, args.out,
                                   show_all=False, only_match=None, phases=phases)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, ".state.json"), "w", encoding="utf-8") as f:
        json.dump({"signature": sig, "generated_at": datetime.now().isoformat(timespec="seconds")},
                  f, ensure_ascii=False, indent=2)

    write_output(args.github_output, True)
    print(f"CHANGED · participants: {len(participants)} · matches rendered: {len(rendered)}"
          f" · signature {sig[:12]}")


if __name__ == "__main__":
    main()
