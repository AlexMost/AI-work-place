#!/usr/bin/env python3
"""Elo ratings for national football teams, computed from the open dataset of
international results (github.com/martj42/international_results, 1872-present).

Uses the eloratings.net formula: K by tournament importance (WC finals 60,
qualifiers/Nations League 40, continental finals 50, friendlies 20, other 30),
goal-difference multiplier, +100 home advantage for non-neutral venues.

Commands:
  ratings  [--top 30]                       current ratings (active teams)
  match    --home A --away B [--not-neutral]  win expectancy + suggested lambdas
  backtest [--from-year 2010]               how often the Elo favorite wins WC matches

The dataset is cached at /tmp/intl_results.csv; pass --refresh AFTER the subcommand to
re-download it (do that during the tournament so group-stage results feed the ratings).
Team names are matched via shared aliases, so modern spellings (Czechia, Türkiye) resolve
to the dataset's names (Czech Republic, Turkey).

Pure Python 3, no dependencies.

Examples:
  elo.py match --home Mexico --away "South Africa"
  elo.py match --home "South Korea" --away Czechia --not-neutral   # host advantage
  elo.py ratings --refresh                                          # re-download mid-tournament
  elo.py backtest
"""

import argparse
import csv
import math
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from team_names import normalize  # noqa: E402

DATA_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
CACHE = "/tmp/intl_results.csv"
HOME_ADVANTAGE = 100  # Elo points, non-neutral venues only

CONTINENTAL_FINALS = ("uefa euro", "copa américa", "african cup of nations",
                      "afc asian cup", "gold cup", "concacaf championship",
                      "fifa confederations cup", "oceania nations cup")


def k_factor(tournament):
    t = tournament.lower()
    if t == "fifa world cup":
        return 60
    if "qualification" in t or "nations league" in t:
        return 40
    if any(t.startswith(c) or c in t for c in CONTINENTAL_FINALS):
        return 50
    if "friendly" in t:
        return 20
    return 30


def goal_multiplier(gd):
    if gd <= 1:
        return 1.0
    if gd == 2:
        return 1.5
    return 1.75 + (gd - 3) / 8


def expectancy(r_home, r_away, neutral):
    d = r_home + (0 if neutral else HOME_ADVANTAGE) - r_away
    return 1 / (1 + 10 ** (-d / 400))


def load_rows(refresh=False):
    if refresh or not os.path.isfile(CACHE):
        print(f"downloading dataset -> {CACHE} ...", file=sys.stderr)
        urllib.request.urlretrieve(DATA_URL, CACHE)
    with open(CACHE, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["home_score"] in ("NA", ""):
                continue
            yield r


def run(refresh=False, backtest_from=None):
    """One chronological pass: ratings, last-seen dates, calibration, backtest stats."""
    ratings, last_seen = {}, {}
    sxx = sxy = 0.0          # goal_diff vs (We-0.5) regression through origin
    total_goals = n_cal = 0
    bt = {"n": 0, "fav_won": 0, "draws": 0, "by_year": {}}

    for r in load_rows(refresh):
        h, a = r["home_team"], r["away_team"]
        gh, ga = int(r["home_score"]), int(r["away_score"])
        neutral = r["neutral"] == "TRUE"
        rh, ra = ratings.get(h, 1500.0), ratings.get(a, 1500.0)
        we = expectancy(rh, ra, neutral)
        year = int(r["date"][:4])

        # calibration sample: modern competitive matches
        if year >= 2010 and "friendly" not in r["tournament"].lower():
            x = we - 0.5
            sxx += x * x
            sxy += x * (gh - ga)
            total_goals += gh + ga
            n_cal += 1

        if backtest_from and r["tournament"] == "FIFA World Cup" and year >= backtest_from:
            fav_is_home = we >= 0.5
            won = (gh > ga) if fav_is_home else (ga > gh)
            y = bt["by_year"].setdefault(year, {"n": 0, "fav_won": 0, "draws": 0})
            for d in (bt, y):
                d["n"] += 1
                d["fav_won"] += won
                d["draws"] += (gh == ga)

        w = 1.0 if gh > ga else (0.0 if gh < ga else 0.5)
        delta = k_factor(r["tournament"]) * goal_multiplier(abs(gh - ga)) * (w - we)
        ratings[h] = rh + delta
        ratings[a] = ra - delta
        last_seen[h] = last_seen[a] = r["date"]

    calib = {"gd_slope": (sxy / sxx) if sxx else 2.4,
             "avg_total_goals": (total_goals / n_cal) if n_cal else 2.5}
    return ratings, last_seen, calib, bt


def find_team(ratings, name):
    target = normalize(name)
    # exact match on normalized names (resolves Czechia->Czech Republic, Türkiye->Turkey, ...)
    for t in ratings:
        if normalize(t) == target:
            return t
    # then unique substring match on normalized names
    hits = [t for t in ratings if target and target in normalize(t)]
    if len(hits) == 1:
        return hits[0]
    if hits:
        sys.exit(f"error: team {name!r} is ambiguous: {', '.join(sorted(hits)[:8])}")
    sample = ", ".join(repr(t) for t in sorted(ratings)[:6]) if ratings else "—"
    sys.exit(f"error: team {name!r} not found. Use the dataset's spelling "
             f"(e.g. 'Czech Republic', 'Turkey', 'United States', 'South Korea'). "
             f"Sample of available names: {sample}")


def main():
    # --refresh lives on a shared parent so it works after any subcommand
    # (e.g. `elo.py ratings --refresh`, `elo.py match --home A --away B --refresh`).
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--refresh", action="store_true", help="re-download the results dataset")

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ratings", parents=[common])
    p.add_argument("--top", type=int, default=30)
    p = sub.add_parser("match", parents=[common])
    p.add_argument("--home", required=True)
    p.add_argument("--away", required=True)
    p.add_argument("--not-neutral", action="store_true",
                   help="real home advantage (+100 Elo), e.g. WC 2026 hosts at home")
    p = sub.add_parser("backtest", parents=[common])
    p.add_argument("--from-year", type=int, default=2010)
    args = ap.parse_args()

    if args.cmd == "backtest":
        _, _, calib, bt = run(args.refresh, backtest_from=args.from_year)
        print(f"World Cup matches {args.from_year}+ — picking the pre-match Elo favorite:")
        for year in sorted(bt["by_year"]):
            y = bt["by_year"][year]
            print(f"  WC {year}: favorite won {y['fav_won']}/{y['n']} = {y['fav_won']/y['n']:.0%}"
                  f"  (draws {y['draws']/y['n']:.0%})")
        if bt["n"]:
            print(f"  TOTAL:   favorite won {bt['fav_won']}/{bt['n']} = {bt['fav_won']/bt['n']:.0%}"
                  f"  (draws {bt['draws']/bt['n']:.0%})")
        print(f"\ncalibration (2010+ competitive): goal_diff ≈ {calib['gd_slope']:.2f}·(We−0.5), "
              f"avg total goals {calib['avg_total_goals']:.2f}")
        return

    ratings, last_seen, calib, _ = run(args.refresh)

    if args.cmd == "ratings":
        active = [(t, r) for t, r in ratings.items() if last_seen[t] >= "2024"]
        active.sort(key=lambda x: -x[1])
        for i, (t, r) in enumerate(active[:args.top], 1):
            print(f"  {i:>3}. {t:<25} {r:7.0f}")
        return

    h = find_team(ratings, args.home)
    a = find_team(ratings, args.away)
    neutral = not args.not_neutral
    we = expectancy(ratings[h], ratings[a], neutral)
    # linear calibration extrapolates badly at extreme expectancies -> cap the edge
    gd = max(-1.8, min(1.8, calib["gd_slope"] * (we - 0.5)))
    total = calib["avg_total_goals"]
    lam_h = max(0.15, (total + gd) / 2)
    lam_a = max(0.15, (total - gd) / 2)
    fav = h if we >= 0.5 else a
    print(f"{h}: {ratings[h]:.0f}  vs  {a}: {ratings[a]:.0f}"
          f"   ({'neutral venue' if neutral else h + ' at home, +100'})")
    print(f"  Elo win expectancy: {h} {we:.1%} — {a} {1 - we:.1%}  -> favorite: {fav}")
    print(f"  suggested expected goals (calibrated on 2010+ matches): {lam_h:.2f} — {lam_a:.2f}")
    print(f"  next: python3 predict_score.py --home {h!r} --away {a!r} --lambdas {lam_h:.2f} {lam_a:.2f}")


if __name__ == "__main__":
    main()
