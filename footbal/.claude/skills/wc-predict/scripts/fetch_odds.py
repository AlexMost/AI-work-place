#!/usr/bin/env python3
"""Consensus 1X2 odds from many bookmakers via The Odds API (the-odds-api.com).

A single bookmaker (favbet) can have skewed lines; the median across 10-20 books
is a far more reliable probability estimate. Free tier: 500 credits/month, one
odds call for ALL matches of a competition = regions x markets credits (so the
default h2h+eu call costs 1 credit). The /sports discovery call is free.

Key: ODDS_API_KEY in .env (register free, no card: https://the-odds-api.com).

Commands:
  sports                          list soccer competitions available right now (free)
  odds [--sport KEY] [--team X]   consensus odds per match; --sport defaults to
                                  auto-discovering the FIFA World Cup competition
       [--totals]                 also fetch Over/Under 2.5 (costs 1 extra credit)

Examples:
  fetch_odds.py odds                       # all WC matches, consensus 1X2
  fetch_odds.py odds --team mexico --totals --json
"""

import argparse
import json
import statistics
import sys
import urllib.parse
import urllib.request

from fetch_stats import load_dotenv  # same .env convention as the stats script
import os

BASE = "https://api.the-odds-api.com/v4"


def get(path, params, key):
    params = {**params, "apiKey": key}
    url = f"{BASE}{path}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            quota = resp.headers.get("x-requests-remaining")
            return json.loads(resp.read().decode()), quota
    except urllib.error.HTTPError as e:
        if e.code == 401:
            sys.exit("error: invalid ODDS_API_KEY (register free: https://the-odds-api.com)")
        if e.code == 429:
            sys.exit("error: The Odds API quota exhausted (500 credits/month on free tier)")
        sys.exit(f"error: HTTP {e.code}: {e.read().decode()[:300]}")


def discover_world_cup(key):
    sports, _ = get("/sports", {}, key)
    hits = [s for s in sports
            if s["key"].startswith("soccer") and "world cup" in s["title"].lower()
            and "winner" not in s["title"].lower()]
    if not hits:
        sys.exit("error: no active FIFA World Cup competition found on The Odds API "
                 "(check `fetch_odds.py sports` for what's available)")
    return hits[0]["key"]


def median_market(bookmakers, market_key, point=None):
    """Median decimal price per outcome name across all bookmakers."""
    prices = {}
    for b in bookmakers:
        for m in b.get("markets", []):
            if m["key"] != market_key:
                continue
            for o in m["outcomes"]:
                if point is not None and o.get("point") != point:
                    continue
                prices.setdefault(o["name"], []).append(o["price"])
    return {name: (round(statistics.median(ps), 3), len(ps)) for name, ps in prices.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sports").add_argument("--json", action="store_true")
    p = sub.add_parser("odds")
    p.add_argument("--json", action="store_true")
    p.add_argument("--sport", help="sport key (default: auto-discover the World Cup)")
    p.add_argument("--team", help="only matches involving this team (substring)")
    p.add_argument("--regions", default="eu")
    p.add_argument("--totals", action="store_true", help="also fetch Over/Under 2.5")
    args = ap.parse_args()

    load_dotenv()
    key = os.environ.get("ODDS_API_KEY")
    if not key:
        sys.exit("error: ODDS_API_KEY not set. Register free (no card) at "
                 "https://the-odds-api.com and add ODDS_API_KEY=... to .env")

    if args.cmd == "sports":
        sports, _ = get("/sports", {}, key)
        for s in sports:
            if s["key"].startswith("soccer"):
                print(f'  {s["key"]:<40} {s["title"]}')
        return

    sport = args.sport or discover_world_cup(key)
    markets = "h2h,totals" if args.totals else "h2h"
    events, quota = get(f"/sports/{sport}/odds",
                        {"regions": args.regions, "markets": markets, "oddsFormat": "decimal"}, key)

    out = []
    for ev in events:
        home, away = ev["home_team"], ev["away_team"]
        if args.team and args.team.lower() not in (home + away).lower():
            continue
        h2h = median_market(ev["bookmakers"], "h2h")
        if not (home in h2h and away in h2h and "Draw" in h2h):
            continue
        (oh, nb), (od, _), (oa, _) = h2h[home], h2h["Draw"], h2h[away]
        rec = {"home": home, "away": away, "kickoff": ev["commence_time"],
               "books": nb, "odds": {"home": oh, "draw": od, "away": oa}}
        if args.totals:
            tot = median_market(ev["bookmakers"], "totals", point=2.5)
            if "Over" in tot and "Under" in tot:
                rec["over25"], rec["under25"] = tot["Over"][0], tot["Under"][0]
        out.append(rec)

    if args.json:
        print(json.dumps({"sport": sport, "credits_remaining": quota, "matches": out},
                         ensure_ascii=False, indent=2))
        return

    print(f"sport: {sport} | matches: {len(out)} | API credits remaining: {quota}")
    for r in out:
        o = r["odds"]
        s = sum(1 / x for x in o.values())
        probs = " / ".join(f"{(1 / o[k]) / s:.0%}" for k in ("home", "draw", "away"))
        print(f'\n{r["home"]} vs {r["away"]} — {r["kickoff"]}')
        print(f'  consensus of {r["books"]} books: {o["home"]} / {o["draw"]} / {o["away"]}'
              f'  -> {probs}')
        extra = f' --over25 {r["over25"]} --under25 {r["under25"]}' if "over25" in r else ""
        print(f'  predict: python3 predict_score.py --home {r["home"]!r} --away {r["away"]!r}'
              f' --odds {o["home"]} {o["draw"]} {o["away"]}{extra}')


if __name__ == "__main__":
    main()
