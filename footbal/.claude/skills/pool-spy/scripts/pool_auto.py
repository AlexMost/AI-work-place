#!/usr/bin/env python3
"""Unattended pool-page updater for GitHub Actions — the automatic counterpart of
`pool_spy.py`.

Gate: a single cheap *probe* decides whether anything changed, and only then is the full
fetch + render done. The probe samples a handful of participants (SAMPLE_N) across phases
and hashes, per match, the match state (status/score/started) plus those members' visible
picks and points. That is enough to catch everything that actually changes while a match
plays — live score, other members' picks being revealed after kickoff, and points being
(re)computed — without paying for the full ~all-members fetch on every run. The full
collect (`pool_spy.collect` → `build_site`, reusing pool_spy.py) runs only when the probe
signature moved.

Sampling several members (not just the token owner, whose own picks are always
self-visible) is what makes the probe able to see a reveal: those events are global —
every member's picks for a match appear at once and all are scored together — so any
sampled member reflects them.

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

SAMPLE_N = 4   # participants sampled by the probe; >1 non-self is enough to see a reveal


def _hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def probe(token, pool_id, sample_n=SAMPLE_N):
    """Cheap change-detection fetch: match metadata + a few members' picks/points.

    Returns (matches_meta, samples) where samples[uid][matchId] = [goals, points].
    Cost ~ sample_n * phases calls, far below the full all-members collect.
    """
    phase_objs = pool_spy.fetch_phases(token)
    phase_ids = [ph.get("id") for ph in phase_objs
                 if ph.get("id") and (ph.get("matchCount") or 0) > 0] or [None]
    participants = pool_spy.fetch_participants(token, pool_id)
    sharers = [p for p in participants if p.get("allowPredictionSharing", True)]
    sampled = sharers[:sample_n]

    matches = {}
    samples = {}
    for p in sampled:
        uid = p["id"]
        for phase_id in phase_ids:
            for entry in pool_spy.fetch_user_predictions(token, uid, pool_id, phase_id):
                m = entry.get("match") or {}
                mid = m.get("matchId")
                if not mid:
                    continue
                matches[mid] = m
                pred = entry.get("prediction") or {}
                h, a = pred.get("homeGoals"), pred.get("awayGoals")
                goals = [h, a] if h is not None and a is not None else None
                samples.setdefault(uid, {})[mid] = [goals, pred.get("pointsEarned")]
    return matches, samples


def probe_signature(matches, samples):
    payload = {
        "m": {mid: [m.get("status"), m.get("homeGoals"), m.get("awayGoals"),
                    pool_spy.has_started(m)]
              for mid, m in matches.items()},
        "s": samples,
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
    matches, samples = probe(token, pool_id)
    sig = probe_signature(matches, samples)

    if not args.force and sig == prev.get("probe_signature"):
        write_output(args.github_output, False)
        print(f"UNCHANGED · matches: {len(matches)} · probe {sig[:12]}")
        return

    participants, full_matches, preds, phases = pool_spy.collect(token, pool_id)
    rendered = pool_spy.build_site(participants, full_matches, preds, args.out,
                                   show_all=False, only_match=None, phases=phases)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, ".state.json"), "w", encoding="utf-8") as f:
        json.dump({"probe_signature": sig,
                   "generated_at": datetime.now().isoformat(timespec="seconds")},
                  f, ensure_ascii=False, indent=2)

    write_output(args.github_output, True)
    print(f"CHANGED · participants: {len(participants)} · matches rendered: {len(rendered)}"
          f" · probe {sig[:12]}")


if __name__ == "__main__":
    main()
