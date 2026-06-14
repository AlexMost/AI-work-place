#!/usr/bin/env python3
"""Compute live progress for the tournament bonus questions and cache it in the ledger.

The pool's bonus questions (+10 each) ask for tournament-wide tallies — total group-stage
goals, the top-scoring country, red cards, penalties, the most-booked country. Two of those
are derivable from finished-match scores; the rest need event-level data the free
football-data tier does not expose (its match detail has only the score and referees — no
bookings/goals/penalties arrays). So:

  * group_goals / top_scorer_country  -> computed automatically from finished results
  * manual (cards, penalties, yellows) -> read from a user-maintained `metric.count`
    (and optional `metric.leader`) in the ledger; this script only reflects them so the
    dashboard shows one consistent "поточний стан" line per question

For each bonus question it writes a `live` block ({headline, sub, progress, status}) back
into predictions.json, which generate_dashboard.py renders. Only the `live` keys change;
the round-trip is byte-stable otherwise. Run this before regenerating the dashboard.

Usage: bonus_stats.py [--ledger predictions.json] [--results results.json]
                      [--dry-run]
Without --results it fetches finished matches itself (football-data, ~1 credit) via
fetch_stats.FootballData. Default ledger path resolves relative to the project root.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_stats import FootballData, load_dotenv  # noqa: E402
from team_names import normalize  # noqa: E402

GROUP_MATCHES_TOTAL = 72   # 12 groups x 6 = 72 group-stage matches (WC-2026, 48 teams)
TOURNAMENT_MATCHES_TOTAL = 104  # 72 group + 32 knockout

# Canonical-key -> Ukrainian display name for the 48 WC-2026 participants, so the live
# leader reads natively (matching the hand-written bonus answers like "Іспанія"). Keyed by
# team_names.normalize() output, which already folds Türkiye/Turkey, USA/United States, etc.
UA_NAME = {
    "mexico": "Мексика", "south africa": "ПАР", "south korea": "Корея",
    "czech republic": "Чехія", "canada": "Канада", "bosnia": "Боснія",
    "united states": "США", "paraguay": "Парагвай", "qatar": "Катар",
    "switzerland": "Швейцарія", "brazil": "Бразилія", "morocco": "Марокко",
    "haiti": "Гаїті", "scotland": "Шотландія", "australia": "Австралія",
    "turkey": "Туреччина", "germany": "Німеччина", "curacao": "Кюрасао",
    "netherlands": "Нідерланди", "japan": "Японія", "ivory coast": "Кот-д'Івуар",
    "ecuador": "Еквадор", "sweden": "Швеція", "tunisia": "Туніс", "spain": "Іспанія",
    "cape verde islands": "Кабо-Верде", "belgium": "Бельгія", "egypt": "Єгипет",
    "saudi arabia": "Саудівська Аравія", "uruguay": "Уругвай", "iran": "Іран",
    "new zealand": "Нова Зеландія", "france": "Франція", "senegal": "Сенегал",
    "iraq": "Ірак", "norway": "Норвегія", "argentina": "Аргентина", "algeria": "Алжир",
    "austria": "Австрія", "jordan": "Йорданія", "portugal": "Португалія",
    "congo dr": "ДР Конго", "dr congo": "ДР Конго", "england": "Англія",
    "croatia": "Хорватія", "ghana": "Гана", "panama": "Панама",
    "uzbekistan": "Узбекистан", "colombia": "Колумбія",
}


def ua(name):
    return UA_NAME.get(normalize(name), name)


def parse_band(answer):
    """('176-200') -> (176, 200); returns None when the answer is not an 'A-B' range."""
    parts = str(answer).split("-")
    if len(parts) == 2 and all(p.strip().isdigit() for p in parts):
        return int(parts[0]), int(parts[1])
    return None


def played(results):
    return [m for m in results if m.get("score") and m["score"][0] is not None]


def live_group_goals(question, results):
    group = [m for m in played(results) if m.get("stage") == "GROUP_STAGE"]
    goals = sum(m["score"][0] + m["score"][1] for m in group)
    n = len(group)
    pace = goals / n if n else 0.0
    proj = round(pace * GROUP_MATCHES_TOTAL)
    band = parse_band(question.get("answer", ""))
    status, band_note = None, ""
    if band:
        lo, hi = band
        status = "below" if proj < lo else ("above" if proj > hi else "in")
        word = {"below": "нижче", "above": "вище", "in": "в межах"}[status]
        band_note = f" ({word} {lo}–{hi})"
    sub = (f"{n}/{GROUP_MATCHES_TOTAL} матчів · темп {pace:.2f}/матч → проєкція ~{proj}{band_note}"
           if n else "ще жодного матчу")
    return {"headline": f"{goals} голів", "sub": sub,
            "progress": round(n / GROUP_MATCHES_TOTAL, 4), "status": status}


def live_top_scorer(question, results):
    totals = {}
    for m in played(results):
        for team, g in ((m["home"], m["score"][0]), (m["away"], m["score"][1])):
            totals[normalize(team)] = totals.get(normalize(team), 0) + g
    if not totals or max(totals.values()) == 0:
        return {"headline": "—", "sub": "ще немає забитих", "progress": None, "status": None}
    top = max(totals.values())
    leaders = sorted(k for k, v in totals.items() if v == top)
    headline = f"{' / '.join(ua(k) for k in leaders[:3])} — {top}"

    pick = question.get("answer", "")           # our bet, e.g. "Іспанія"
    pick_key = next((k for k in totals if ua(k) == pick), None)
    if pick and any(ua(k) == pick for k in leaders):
        sub = "наш пік лідирує ✓"
    elif pick_key is not None:
        sub = f"наш пік {pick}: {totals[pick_key]} (лідер {top})"
    elif pick:
        sub = f"наш пік {pick} ще не забивав"
    else:
        sub = ""
    return {"headline": headline, "sub": sub, "progress": None, "status": None}


def live_manual(question, results):
    m = question.get("metric", {})
    count = m.get("count", 0)
    unit = m.get("unit", "")
    leader = m.get("leader")
    n = len(played(results))
    headline = f"{leader} — {count}" if leader else f"{count} {unit}".strip()
    sub = f"введено вручну · зіграно {n}/{TOURNAMENT_MATCHES_TOTAL} матчів"
    return {"headline": headline, "sub": sub,
            "progress": round(n / TOURNAMENT_MATCHES_TOTAL, 4), "status": None}


BUILDERS = {
    "group_goals": live_group_goals,
    "top_scorer_country": live_top_scorer,
    "manual": live_manual,
}


def update(ledger, results):
    """Set each bonus question's `live` block in place; return a list of (q, live) for printing."""
    out = []
    for q in ledger.get("bonus_questions", []):
        kind = (q.get("metric") or {}).get("kind")
        builder = BUILDERS.get(kind)
        if not builder:
            continue
        q["live"] = builder(q, results)
        out.append((q.get("q", ""), q["live"]))
    return out


def main():
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=os.path.join(root, "predictions.json"))
    ap.add_argument("--results", help="fetch_stats.py results --json output; else fetched live")
    ap.add_argument("--dry-run", action="store_true", help="print only, do not write the ledger")
    args = ap.parse_args()

    with open(args.ledger, encoding="utf-8") as f:
        ledger = json.load(f)

    if args.results:
        with open(args.results, encoding="utf-8") as f:
            results = json.load(f)
    else:
        load_dotenv()
        token = os.environ.get("FOOTBALL_DATA_TOKEN")
        if not token:
            sys.exit("error: no FOOTBALL_DATA_TOKEN in env/.env; pass --results instead.")
        results = FootballData(token).results(120)

    rows = update(ledger, results)
    for q, live in rows:
        print(f"• {q}\n    {live['headline']}  —  {live['sub']}")
    if not rows:
        print("no bonus questions with a `metric` block found in the ledger.")

    if args.dry_run:
        print("\n(dry run — ledger not written)")
        return
    with open(args.ledger, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"\nledger updated: {args.ledger}")


if __name__ == "__main__":
    main()
