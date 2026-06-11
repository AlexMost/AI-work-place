#!/usr/bin/env python3
"""Pre-match check: do the ledger's upcoming picks still hold against fresh odds?

Predictions are editable until 15 minutes before kickoff, and the market keeps
absorbing news (lineups, injuries, weather) right up to then — so instead of
checking those signals by hand, re-fetch consensus odds shortly before kickoff,
refit the model, and compare the fresh best-EV pick with what's in the ledger.

One Odds API call covers every upcoming match (h2h + totals = 2 credits).
This script NEVER writes the ledger — it only reports; re-predicting and
upserting stays a user decision (see the protocol in the project CLAUDE.md).

Usage:
  prematch_check.py [--hours 48] [--team X] [--json]
                    [--ledger PATH] [--sport KEY] [--regions eu]
                    [--events-json FILE]   # offline: use a saved /odds payload
                                           # instead of the live API call

Exit codes: 0 = all picks hold (or nothing to check); 1 = fatal (key/HTTP/quota);
3 = attention needed (a pick changed, or an upcoming match is missing from the
market feed). 2 is reserved by argparse.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stats import load_dotenv  # noqa: E402
from fetch_odds import get, discover_world_cup, median_market  # noqa: E402
from team_names import normalize  # noqa: E402
from generate_dashboard import model_view, stage_mult  # noqa: E402
from predict_score import (  # noqa: E402
    demargin_power, fit_lambdas, score_matrix, outcome_probs, ev_ranking,
    MAX_GOALS, DEFAULT_RHO,
)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "..", "..", "..", ".."))
MOVE_NOTE_PP = 0.03  # outcome-probability move worth calling out explicitly


def parse_kickoff(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def stored_market(m):
    """(odds_list, probs, rho) from a model snapshot, tolerating both ledger shapes:
    full snapshot (odds dict, implied_probabilities, dixon_coles_rho) and the
    legacy compact form (odds list, probs, rho)."""
    if not m:
        return None, None, None
    odds = m.get("odds")
    if isinstance(odds, dict):
        odds = [odds.get("home"), odds.get("draw"), odds.get("away")]
    probs = m.get("implied_probabilities") or m.get("probs")
    rho = m.get("dixon_coles_rho", m.get("rho"))
    return odds, probs, rho


def check_entry(p, ev, scoring):
    """Refit one ledger entry against a fresh odds event. Returns the result dict;
    raises KeyError only if the payload lacks a full 1X2 market (caller guards)."""
    flipped = normalize(ev["home_team"]) != normalize(p["home"])
    h2h = median_market(ev["bookmakers"], "h2h")
    (oh, books), (od, _), (oa, _) = (h2h[ev["home_team"]], h2h["Draw"],
                                     h2h[ev["away_team"]])
    if flipped:
        oh, oa = oa, oh
    tot = median_market(ev["bookmakers"], "totals", point=2.5)
    fresh_ou = (tot["Over"][0], tot["Under"][0]) if ("Over" in tot and "Under" in tot) else None

    p_home, p_draw, p_away = demargin_power((oh, od, oa))
    _, stored_probs, stored_rho = stored_market(p.get("model"))
    if fresh_ou:
        p_over = demargin_power(fresh_ou)[0]
        lam_h, lam_a, rho = fit_lambdas(p_home, p_away, p_over)
    else:
        # no fresh totals: keep the snapshot's fitted rho so a pick change can only
        # come from market movement, not from a silently swapped prior
        rho = stored_rho if stored_rho is not None else DEFAULT_RHO
        lam_h, lam_a, rho = fit_lambdas(p_home, p_away, None, rho=rho)

    matrix = score_matrix(lam_h, lam_a, rho, MAX_GOALS)
    m_h, m_d, m_a, _ = outcome_probs(matrix)
    ranking = ev_ranking(matrix, {"home": m_h, "draw": m_d, "away": m_a},
                         scoring["exact"], scoring["outcome"])
    bi, bj, bp, bev = ranking[0]

    predicted = p.get("predicted")
    mult = stage_mult(p.get("stage", "group"))
    ev_keep = next((e for i, j, _, e in ranking
                    if predicted and [i, j] == list(predicted)), None)
    changed = bool(predicted) and [bi, bj] != list(predicted)

    fresh_probs = {"home": p_home, "draw": p_draw, "away": p_away}
    delta_pp = ({k: round((fresh_probs[k] - stored_probs[k]) * 100, 1)
                 for k in ("home", "draw", "away")} if stored_probs else None)

    model_rec = model_view(p.get("model"))["rec"]
    return {
        "home": p["home"], "away": p["away"], "kickoff": p.get("kickoff"),
        "stage": p.get("stage", "group"),
        "status": "CHANGED" if changed else "OK",
        "predicted": predicted,
        "new_best": {"score": f"{bi}-{bj}", "probability": round(bp, 4),
                     "expected_points": round(bev * mult, 3)},
        "ev_drop_if_keeping": (round((bev - ev_keep) * mult, 3)
                               if ev_keep is not None else None),
        "odds": {"stored": stored_market(p.get("model"))[0],
                 "fresh": [oh, od, oa]},
        "probs_delta_pp": delta_pp,
        "books": books,
        "totals_missing": fresh_ou is None,
        "user_override": bool(model_rec and predicted
                              and list(model_rec) != list(predicted)),
    }


def fmt_entry(r):
    mult2 = " · плей-оф ×2" if str(r["stage"]).lower() != "group" else ""
    head = (f'{r["home"]} vs {r["away"]} — '
            f'{str(r["kickoff"])[:16].replace("T", " ")} UTC{mult2}')
    if r["status"] == "NO_MARKET":
        return f"{head}\n  ⚠ ринок недоступний (матч відсутній у фіді — кікоф близько?)"
    pred = f'{r["predicted"][0]}:{r["predicted"][1]}' if r["predicted"] else "—"
    nb = r["new_best"]
    line = (f'  стоїть {pred} · свіжий best-EV {nb["score"].replace("-", ":")} '
            f'(P {nb["probability"]:.1%}, EV {nb["expected_points"]:.2f})')
    if r["status"] == "CHANGED":
        cost = (f' — лишити {pred} коштує {r["ev_drop_if_keeping"]:.2f} бала'
                if r["ev_drop_if_keeping"] is not None else "")
        verdict = (f'  ЗМІНИВСЯ{cost}'
                   + ("\n  (прогноз і так відрізнявся від моделі — свідомий вибір?)"
                      if r["user_override"] else ""))
    else:
        verdict = "  OK — пік тримається"
    notes = []
    if r["totals_missing"]:
        notes.append("без свіжих тоталів — ρ зі снапшота")
    if r["probs_delta_pp"]:
        big = {k: v for k, v in r["probs_delta_pp"].items()
               if abs(v) >= MOVE_NOTE_PP * 100}
        d = r["probs_delta_pp"]
        notes.append(f'рух ринку H {d["home"]:+.1f} / X {d["draw"]:+.1f} / '
                     f'A {d["away"]:+.1f} п.п.' + (" — суттєвий" if big else ""))
    notes.append(f'{r["books"]} книг')
    return f"{head}\n{line}\n{verdict}\n  ({'; '.join(notes)})"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hours", type=float, default=48,
                    help="check entries kicking off within this window (default 48)")
    ap.add_argument("--ledger", default=os.path.join(ROOT, "predictions.json"))
    ap.add_argument("--sport", help="Odds API sport key (default: auto-discover the World Cup)")
    ap.add_argument("--regions", default="eu")
    ap.add_argument("--team", help="only entries involving this team (substring)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--events-json",
                    help="path to a saved /odds payload — skips the live API call")
    args = ap.parse_args()

    with open(args.ledger, encoding="utf-8") as f:
        ledger = json.load(f)
    scoring = ledger.get("scoring", {"exact": 8, "outcome": 5})

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(hours=args.hours)
    pending = []
    for p in ledger.get("predictions", []):
        if p.get("actual"):
            continue
        if args.team and args.team.lower() not in (p.get("home", "") + p.get("away", "")).lower():
            continue
        ko = parse_kickoff(p.get("kickoff"))
        if ko and now <= ko <= horizon:
            pending.append(p)
    if not pending:
        print(f"у вікні {args.hours:g} год немає матчів без результату — нічого перевіряти")
        return 0

    quota = None
    if args.events_json:
        with open(args.events_json, encoding="utf-8") as f:
            events = json.load(f)
    else:
        load_dotenv()
        key = os.environ.get("ODDS_API_KEY")
        if not key:
            sys.exit("error: ODDS_API_KEY not set (or use --events-json for offline mode)")
        sport = args.sport or discover_world_cup(key)
        events, quota = get(f"/sports/{sport}/odds",
                            {"regions": args.regions, "markets": "h2h,totals",
                             "oddsFormat": "decimal"}, key)

    by_pair = {frozenset((normalize(e["home_team"]), normalize(e["away_team"]))): e
               for e in events}

    results = []
    for p in pending:
        ev = by_pair.get(frozenset((normalize(p["home"]), normalize(p["away"]))))
        if not ev:
            results.append({"home": p["home"], "away": p["away"],
                            "kickoff": p.get("kickoff"), "stage": p.get("stage", "group"),
                            "status": "NO_MARKET", "predicted": p.get("predicted")})
            continue
        try:
            results.append(check_entry(p, ev, scoring))
        except KeyError:  # h2h market incomplete for this event
            results.append({"home": p["home"], "away": p["away"],
                            "kickoff": p.get("kickoff"), "stage": p.get("stage", "group"),
                            "status": "NO_MARKET", "predicted": p.get("predicted")})

    attention = any(r["status"] in ("CHANGED", "NO_MARKET") for r in results)
    if args.json:
        print(json.dumps({"checked_at": now.isoformat(timespec="minutes"),
                          "credits_remaining": quota, "entries": results},
                         ensure_ascii=False, indent=2))
    else:
        for r in results:
            print(fmt_entry(r))
            print()
        n_ch = sum(1 for r in results if r["status"] == "CHANGED")
        n_no = sum(1 for r in results if r["status"] == "NO_MARKET")
        tail = f"перевірено {len(results)}: змінилось {n_ch}, без ринку {n_no}"
        if quota is not None:
            tail += f" · кредитів лишилось {quota}"
        print(tail)
    return 3 if attention else 0


if __name__ == "__main__":
    sys.exit(main())
