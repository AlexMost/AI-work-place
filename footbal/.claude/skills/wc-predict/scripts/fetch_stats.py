#!/usr/bin/env python3
"""Fetch team statistics from free football APIs (football-data.org or api-football.com).

Provider is auto-detected from available credentials:
  - env FOOTBALL_DATA_TOKEN  -> football-data.org  (v4, free tier includes World Cup, 10 req/min)
  - env API_FOOTBALL_KEY     -> api-football.com   (v3, free tier 100 req/day)
Override with --provider / --token.

Commands:
  teams    --name "Mexico"                  find team id(s) by name
  form     --team-id 770 [--last 10]        recent results, W-D-L, avg goals for/against
  h2h      --team1 770 --team2 801          head-to-head record between two teams
  fixtures [--limit 20]                     upcoming World Cup fixtures (football-data only)
  results  [--limit 120]                    finished WC matches, 90-MINUTE score (football-data
                                            only; api-football free plan has no WC-2026 access)

Scores are reported AFTER 90 minutes: for knockout matches decided in extra time or on
penalties, regularTime is used (the pool ignores ET/shootouts), and "duration"/"stage" are
included so the caller can tell group from playoff and spot ET/PEN matches.

All commands accept --json for machine-readable output. Pure Python 3, no dependencies.
"""

import argparse
import json
import os
import sys
from datetime import date, timedelta
import urllib.error
import urllib.parse
import urllib.request

FD_BASE = "https://api.football-data.org/v4"
AF_BASE = "https://v3.football.api-sports.io"


def ninety_minute_score(score):
    """The score after 90 minutes from a football-data v4 score object.

    For knockout matches in extra time or penalties, fullTime includes ET (and even
    shootout) goals; the pool counts only the 90' result, so use regularTime when the
    match was not decided in regular time.
    """
    duration = score.get("duration", "REGULAR")
    rt = score.get("regularTime")
    if duration != "REGULAR" and rt and rt.get("home") is not None:
        return rt
    return score["fullTime"]


def load_dotenv():
    """Load the nearest .env file (cwd upwards, then this script's dir upwards).

    Lets the user keep API keys in e.g. footbal/.env instead of shell config.
    Real environment variables always win; the first .env found is used.
    """
    candidates = []
    for start in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        d = start
        while True:
            candidates.append(os.path.join(d, ".env"))
            parent = os.path.dirname(d)
            if parent == d:
                break
            d = parent
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("export "):
                    line = line[len("export "):]
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        return


def api_get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit(f"error: API rejected the token (HTTP {e.code}). Check your key. URL: {url}")
        if e.code == 429:
            sys.exit("error: rate limit hit (HTTP 429). football-data free tier = 10 req/min, "
                     "api-football free tier = 100 req/day. Wait and retry.")
        sys.exit(f"error: HTTP {e.code} for {url}: {e.read().decode()[:300]}")


class FootballData:
    """football-data.org v4 client."""

    name = "football-data.org"

    def __init__(self, token):
        self.h = {"X-Auth-Token": token}

    def teams(self, query):
        data = api_get(f"{FD_BASE}/competitions/WC/teams", self.h)
        q = query.lower()
        hits = [t for t in data.get("teams", [])
                if q in t["name"].lower() or q in (t.get("shortName") or "").lower()
                or q == (t.get("tla") or "").lower()]
        return [{"id": t["id"], "name": t["name"], "short": t.get("tla")} for t in hits]

    def _team_matches(self, team_id, limit):
        # the API silently defaults to a narrow date window -> ask for 2 years explicitly
        today = date.today()
        url = (f"{FD_BASE}/teams/{team_id}/matches?status=FINISHED&limit={limit}"
               f"&dateFrom={today - timedelta(days=730)}&dateTo={today}")
        data = api_get(url, self.h)
        out = []
        for m in data.get("matches", []):
            ft = ninety_minute_score(m["score"])
            if ft["home"] is None:
                continue
            out.append({
                "date": m["utcDate"][:10],
                "home": m["homeTeam"]["name"], "home_id": m["homeTeam"]["id"],
                "away": m["awayTeam"]["name"], "away_id": m["awayTeam"]["id"],
                "score": f'{ft["home"]}-{ft["away"]}',
                "gh": ft["home"], "ga": ft["away"],
                "competition": m["competition"]["name"],
            })
        out.sort(key=lambda m: m["date"], reverse=True)
        return out

    def form(self, team_id, last):
        return self._team_matches(team_id, max(last, 10))[:last]

    def h2h(self, team1, team2, last):
        ms = self._team_matches(team1, 100)
        return [m for m in ms if team2 in (m["home_id"], m["away_id"])][:last]

    def fixtures(self, limit):
        data = api_get(f"{FD_BASE}/competitions/WC/matches?status=SCHEDULED", self.h)
        out = []
        for m in data.get("matches", [])[:limit]:
            out.append({"date": m["utcDate"], "home": m["homeTeam"]["name"] or "TBD",
                        "away": m["awayTeam"]["name"] or "TBD",
                        "stage": m.get("stage"), "group": m.get("group")})
        return out

    def results(self, limit):
        data = api_get(f"{FD_BASE}/competitions/WC/matches?status=FINISHED", self.h)
        out = []
        for m in data.get("matches", [])[-limit:]:
            ft = ninety_minute_score(m["score"])
            out.append({"date": m["utcDate"][:10], "home": m["homeTeam"]["name"],
                        "away": m["awayTeam"]["name"], "score": [ft["home"], ft["away"]],
                        "duration": m["score"].get("duration"), "stage": m.get("stage"),
                        "group": m.get("group")})
        return out


class ApiFootball:
    """api-football.com (api-sports.io) v3 client."""

    name = "api-football.com"

    def __init__(self, token):
        self.h = {"x-apisports-key": token}

    def _get(self, url):
        # api-football returns HTTP 200 with an "errors" object on plan/param problems
        data = api_get(url, self.h)
        errors = data.get("errors")
        if errors:
            sys.exit(f"error from api-football: {errors}")
        return data

    def teams(self, query):
        url = f"{AF_BASE}/teams?search={urllib.parse.quote(query)}"
        data = self._get(url)
        hits = data.get("response", [])
        # national teams first: that's what World Cup predictions need
        hits.sort(key=lambda t: not t["team"].get("national", False))
        return [{"id": t["team"]["id"], "name": t["team"]["name"],
                 "national": t["team"].get("national", False)} for t in hits[:10]]

    def _fixtures_to_matches(self, fixtures):
        out = []
        for f in fixtures:
            if f["fixture"]["status"]["short"] not in ("FT", "AET", "PEN"):
                continue
            out.append({
                "date": f["fixture"]["date"][:10],
                "home": f["teams"]["home"]["name"], "home_id": f["teams"]["home"]["id"],
                "away": f["teams"]["away"]["name"], "away_id": f["teams"]["away"]["id"],
                "score": f'{f["goals"]["home"]}-{f["goals"]["away"]}',
                "gh": f["goals"]["home"], "ga": f["goals"]["away"],
                "competition": f["league"]["name"],
            })
        out.sort(key=lambda m: m["date"], reverse=True)
        return out

    def form(self, team_id, last):
        # free plan: no "last" param and only seasons 2022-2024 -> walk seasons newest-first
        matches = []
        for season in (2024, 2023, 2022):
            data = self._get(f"{AF_BASE}/fixtures?team={team_id}&season={season}")
            matches.extend(self._fixtures_to_matches(data.get("response", [])))
            if len(matches) >= last:
                break
        matches.sort(key=lambda m: m["date"], reverse=True)
        return matches[:last]

    def h2h(self, team1, team2, last):
        # no "last" param on the free plan; the endpoint returns full history anyway
        data = self._get(f"{AF_BASE}/fixtures/headtohead?h2h={team1}-{team2}")
        return self._fixtures_to_matches(data.get("response", []))[:last]

    def fixtures(self, limit):
        sys.exit("error: 'fixtures' is only implemented for football-data.org "
                 "(api-football needs a league id + season; use form/h2h instead)")

    def results(self, limit):
        sys.exit("error: 'results' is only implemented for football-data.org "
                 "(api-football free plan cannot see season 2026 at all)")


def summarize_form(team_id, matches):
    """W-D-L record and goal averages from this team's perspective."""
    w = d = l = gf = ga = 0
    results = []
    for m in matches:
        mine, theirs = (m["gh"], m["ga"]) if m["home_id"] == team_id else (m["ga"], m["gh"])
        gf += mine
        ga += theirs
        r = "W" if mine > theirs else ("L" if mine < theirs else "D")
        w, d, l = w + (r == "W"), d + (r == "D"), l + (r == "L")
        results.append(r)
    n = max(len(matches), 1)
    return {"played": len(matches), "record": f"{w}W-{d}D-{l}L", "results": results,
            "avg_scored": round(gf / n, 2), "avg_conceded": round(ga / n, 2)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--provider", choices=["football-data", "api-football"])
    ap.add_argument("--token", help="API key (else env FOOTBALL_DATA_TOKEN / API_FOOTBALL_KEY)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("teams")
    p.add_argument("--name", required=True)
    parsers = [p]
    p = sub.add_parser("form")
    p.add_argument("--team-id", type=int, required=True)
    p.add_argument("--last", type=int, default=10)
    parsers.append(p)
    p = sub.add_parser("h2h")
    p.add_argument("--team1", type=int, required=True)
    p.add_argument("--team2", type=int, required=True)
    p.add_argument("--last", type=int, default=10)
    parsers.append(p)
    p = sub.add_parser("fixtures")
    p.add_argument("--limit", type=int, default=20)
    parsers.append(p)
    p = sub.add_parser("results")
    p.add_argument("--limit", type=int, default=120,
                   help="how many finished matches (default 120 covers the whole tournament; "
                        "a smaller limit silently drops older matches during catch-up)")
    parsers.append(p)
    for p in parsers:
        p.add_argument("--json", action="store_true")
    args = ap.parse_args()

    load_dotenv()
    fd_token = os.environ.get("FOOTBALL_DATA_TOKEN")
    af_token = os.environ.get("API_FOOTBALL_KEY")
    provider = args.provider
    if provider is None:
        if fd_token and af_token:
            # route by free-plan strengths: api-football has deep form/h2h history,
            # football-data has the WC fixtures feed
            provider = "football-data" if args.cmd in ("fixtures", "results") else "api-football"
        elif af_token:
            provider = "api-football"
        else:
            provider = "football-data"
    if provider == "football-data":
        token = args.token or fd_token
        if not token:
            sys.exit("error: no API key found. Put FOOTBALL_DATA_TOKEN "
                     "(https://www.football-data.org/client/register) or API_FOOTBALL_KEY "
                     "(https://dashboard.api-football.com/register) in .env, or pass --token.")
        client = FootballData(token)
    else:
        token = args.token or af_token
        client = ApiFootball(token)

    if args.cmd == "teams":
        res = client.teams(args.name)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        elif not res:
            print(f"no teams matching {args.name!r} via {client.name}")
        else:
            for t in res:
                extra = " (national)" if t.get("national") else ""
                print(f'{t["id"]:>6}  {t["name"]}{extra}')

    elif args.cmd == "form":
        matches = client.form(args.team_id, args.last)
        summary = summarize_form(args.team_id, matches)
        if args.json:
            print(json.dumps({"summary": summary, "matches": matches}, ensure_ascii=False, indent=2))
        else:
            print(f"last {len(matches)} matches (team {args.team_id}, via {client.name}):")
            for m in matches:
                print(f'  {m["date"]}  {m["home"]} {m["score"]} {m["away"]}  [{m["competition"]}]')
            print(f'  form: {"".join(summary["results"])}  ({summary["record"]})')
            print(f'  avg scored {summary["avg_scored"]} | avg conceded {summary["avg_conceded"]}')

    elif args.cmd == "h2h":
        matches = client.h2h(args.team1, args.team2, args.last)
        summary = summarize_form(args.team1, matches)
        if args.json:
            print(json.dumps({"summary_for_team1": summary, "matches": matches},
                             ensure_ascii=False, indent=2))
        elif not matches:
            print("no head-to-head matches found (football-data only sees ~100 recent "
                  "matches per team; api-football reaches further back)")
        else:
            print(f"head-to-head, team {args.team1} vs {args.team2} (via {client.name}):")
            for m in matches:
                print(f'  {m["date"]}  {m["home"]} {m["score"]} {m["away"]}  [{m["competition"]}]')
            print(f'  record for team {args.team1}: {summary["record"]}')

    elif args.cmd == "fixtures":
        res = client.fixtures(args.limit)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            for f in res:
                grp = f' [{f["group"]}]' if f.get("group") else ""
                print(f'  {f["date"]}  {f["home"]} vs {f["away"]}{grp}')

    elif args.cmd == "results":
        res = client.results(args.limit)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        elif not res:
            print("no finished matches yet")
        else:
            for f in res:
                grp = f' [{f["group"]}]' if f.get("group") else ""
                et = ' (90′ score; ET/PEN ignored)' if f.get("duration") not in (None, "REGULAR") else ""
                print(f'  {f["date"]}  {f["home"]} {f["score"][0]}-{f["score"][1]} {f["away"]}{grp}{et}')


if __name__ == "__main__":
    main()
