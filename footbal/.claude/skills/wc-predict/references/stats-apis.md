# Free football stats APIs

`scripts/fetch_stats.py` supports two providers. Keys live in the project root `.env`
(`footbal/.env`) — the script finds it automatically (cwd upwards, then skill dir
upwards); real env vars override `.env`.

| | football-data.org | api-football.com |
|---|---|---|
| .env key | `FOOTBALL_DATA_TOKEN` | `API_FOOTBALL_KEY` |
| register | https://www.football-data.org/client/register | https://dashboard.api-football.com/register |
| free limits | 10 requests/min | 100 requests/day |
| WC 2026 fixtures | **yes** (`fixtures` command) | not implemented here |
| national-team form | only WC matches → empty before the tournament, fills during it | **yes** (seasons 2022–2024 on free plan; spills into 2025 where a season crosses years) |
| head-to-head | shallow (filters team's recent matches) | **deep history** (verified back to 2010) |

With both keys configured the script auto-routes: `fixtures` → football-data,
`form`/`h2h` → api-football. Override with `--provider` if needed.

Free-plan quirks discovered live (June 2026), already handled by the script:
- api-football rejects the `last` parameter and seasons outside 2022–2024 on free plans;
  the script walks seasons newest-first instead and surfaces plan errors loudly.
- football-data defaults to a narrow date window; the script requests 2 years explicitly.
- api-football signals errors inside an HTTP-200 body (`errors` object), not status codes.

Mind the budgets: api-football = 100 requests/day total (a form call = 1–3 requests,
h2h = 1), so a 9-match matchday with form+h2h for every match ≈ 30–60 requests — fine
once, wasteful if re-run repeatedly. Cache results in the conversation; don't re-fetch
what you already have.

## Commands

```bash
python3 scripts/fetch_stats.py teams --name "Mexico"          # find team id (national teams first)
python3 scripts/fetch_stats.py form --team-id 16 --last 10    # recent results + averages
python3 scripts/fetch_stats.py h2h --team1 16 --team2 1531    # head-to-head
python3 scripts/fetch_stats.py fixtures --limit 20            # upcoming WC matches
python3 scripts/fetch_stats.py results --limit 120            # finished WC matches, 90' score
```

`results` is football-data only (api-football free plan has no WC-2026 access) and returns
the **90-minute** score plus `duration`/`stage` (extra time and shootouts excluded, per the
pool rule). Keep `--limit` high (default 120) — a small limit silently drops older matches
during a mid-tournament catch-up.

Add `--json` for machine-readable output (use that when assembling the HTML report).
Note: team ids differ between providers — always resolve ids with `teams` on the same
provider you'll query (api-football: Mexico=16, South Africa=1531; football-data:
Mexico=769, South Africa=774).

## Using stats when odds are unavailable

Preferred fallback — Elo (opponent-adjusted by construction):

```bash
python3 scripts/elo.py match --home Mexico --away "South Africa" [--not-neutral]
# prints win expectancy + a calibrated --lambdas pair ready for predict_score.py
```

Cruder alternative from recent goal averages (beware minnow-bashing inflation in
continental qualifiers — opposition quality is NOT adjusted for):

```
lambda_home = (home.avg_scored + away.avg_conceded) / 2
lambda_away = (away.avg_scored + home.avg_conceded) / 2
python3 scripts/predict_score.py --home X --away Y --lambdas 1.4 0.9
```

Either way, say the prediction is lower-confidence and prefer odds whenever they exist.
Odds already price in lineups, injuries and motivation — stats are the fallback and the
context, not the primary signal.

## Other free WC-2026 sources (researched June 2026)

- **The Odds API** (the-odds-api.com, `ODDS_API_KEY`): consensus bookmaker odds — see
  `scripts/fetch_odds.py`. Free 500 credits/month; one h2h call for the whole WC = 1 credit.
- **openfootball/worldcup.json** (GitHub, keyless, public domain): all 104 WC-2026
  fixtures, groups, official squads; results updated ~daily during the tournament.
  `https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json`
- **TheSportsDB** (free key `123`, 30 req/min): WC-2026 fixtures under league id 4429;
  results delayed, endpoints capped. Usable as a last-resort fallback.
- **Not worth it**: Sportmonks (WC-2026 is paid-only, €69/mo), worldcupjson.net (dormant
  since 2022), balldontlie FIFA API (free tier has no match data).

## Team-strength ratings (verified June 2026)

- **eloratings.net** serves machine-readable TSVs, updated daily after match days:
  `https://eloratings.net/World.tsv` (all teams) and
  `https://eloratings.net/2026_World_Cup.tsv` (WC participants only). No header row;
  columns start `rank, local_rank, team_code, rating, ...`. Gotchas: team codes are
  site-specific (map via `https://eloratings.net/en.teams.tsv`) and negative numbers use
  Unicode minus (U+2212). Our own `scripts/elo.py` tracks it closely (same top-3), so
  use the site as a cross-check, not a replacement.
- **FIFA live ranking**, keyless JSON:
  `https://api.fifa.com/api/v3/fifarankings/rankings/live?gender=1&sportType=0&language=en`
  (fields `Rank`, `TotalPoints`, `IdCountry` ISO-3, `TeamName`). Weaker predictor than
  Elo — secondary signal only.
- **Dead/stale, do not use**: FiveThirtyEight SPI (redirects since 2025, data frozen
  2023), GitHub/Kaggle FIFA-ranking mirrors (stale since 2022–2024).

## What the free tiers can and cannot feed a model (probed live, June 2026)

- football-data free: WC-2026 fixtures, results, group standings, 26-man squads + coach.
  No match statistics (shots/possession/xG), no player stats.
- api-football free: NO World Cup 2026 access at all (seasons 2022–2024 only) — use it
  for pre-tournament form/h2h and current squads; in-tournament results come from
  football-data or the Elo dataset refresh.
- Neither free tier offers xG, injuries, or player ratings — the V3-style ML model needs
  paid data; odds + Poisson + Elo cross-check is the practical ceiling here.
