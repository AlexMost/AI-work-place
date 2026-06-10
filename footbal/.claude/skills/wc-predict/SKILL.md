---
name: wc-predict
description: Predict football/soccer match results and exact scorelines from bookmaker odds and team statistics using a Poisson model, then render an HTML report that opens in the browser. Use whenever the user asks to predict a football match or score, wants to fill in World Cup (or any tournament) score predictions for their prediction game, mentions betting odds or favbet, pastes a screenshot of fixtures or odds, or asks "який рахунок поставити" / "what score should I predict" — even if they only name two teams.
---

# wc-predict — football score predictions

Pipeline: decimal 1X2 odds → de-margined probabilities → Poisson expected-goals model →
scoreline probabilities → expected-points recommendation → HTML report. The user plays a
friendly prediction game (exact score earns more points than just the correct outcome),
so the recommendation maximizes expected game points, not just "who wins".

## Workflow

### 1. Identify the matches

From the user's message, a screenshot of their prediction site, or upcoming fixtures
(`python3 scripts/fetch_stats.py fixtures`). Note prediction deadlines if visible —
predictions are useless after the deadline, so mention soon-closing ones first.

### 2. Get the odds (the primary signal)

Decimal 1X2 odds per match. Priority:

1. **Consensus odds** — if `ODDS_API_KEY` is in `.env`, run
   `python3 scripts/fetch_odds.py odds [--team X] [--totals]`: the median across
   10–20 bookmakers beats any single book's line and outputs ready-to-run
   `predict_score.py` commands. One call covers the whole competition.
2. **favbet.hr** (the user's bookmaker) — read `references/favbet-odds.md` before
   scraping: Chrome DevTools MCP → WebFetch (rarely works).
3. **Ask the user** to paste odds or a screenshot.

Never invent odds from memory — every downstream number inherits the error. With no odds
at all, fall back to team-stats lambdas (`references/stats-apis.md`) and say the
prediction is lower-confidence.

### 3. Get team stats (context + sanity check)

If `FOOTBALL_DATA_TOKEN` or `API_FOOTBALL_KEY` is set, fetch recent form and head-to-head
via `scripts/fetch_stats.py` (details and rate limits: `references/stats-apis.md`).
No key → skip stats silently, but tell the user once how to get a free key.
Stats provide the report's form/h2h sections; odds stay the primary signal.

### 4. Run the model per match

```bash
python3 scripts/predict_score.py --home Mexico --away "South Africa" \
  --odds 1.65 3.6 5.5 [--over25 1.9 --under25 1.9] [--json]
```

- Resolve script paths relative to this skill's directory.
- Scoring defaults match the user's pool: 8 points exact / 5 points correct outcome
  (group stage); playoff doubles both (16/10) — same ratio, so per-match picks don't
  change. At 8:5 the outcome term dominates the EV: usually pick the most probable
  outcome's most probable scoreline (unlike steep schemes like 3:1 where a concentrated
  0-0 can beat a slight favorite).
- Playoff predictions count the 90-minute result — a draw IS a valid playoff prediction
  and often an undervalued one in even matches (friends betting "with the heart" rarely
  pick it). Bookmaker 1X2 odds price exactly the 90-minute result, so the model applies
  unchanged.
- Use `--json` output when assembling the report.

### 5. Sanity-check

Compare the model's top scorelines with `references/historical-scores.md`. Football
scores cluster hard around 1-0 / 2-1 / 1-1 / 2-0; an exotic recommendation (4-2, 3-3)
almost always means bad odds input — re-check before presenting.

### 6. Present: chat summary + HTML report

Write the matches to a JSON file (schema in the docstring of
`scripts/generate_report.py` — each match carries an ISO `kickoff` and the
`predict_score.py --json` output) and render:

```bash
python3 scripts/generate_report.py --input /tmp/predictions.json
```

This writes **one self-contained HTML file per match** to `reports/`, named
deterministically (`wc-report-<date>-<home>-vs-<away>.html`) so re-predicting a match
overwrites its file rather than piling up duplicates. A single-match input opens in the
browser; a multi-match input doesn't (the dashboard links them all). In chat, also give a
compact table — match, recommended score, win probability — in the user's language (the
user writes Ukrainian), so they can fill in their prediction site without switching
windows. Flag toss-up matches (no outcome above ~40%) honestly instead of feigning
confidence, and remind that even a perfect model hits the exact score only ~10–17% of
the time — the edge comes from being consistently on the most probable side.

### 7. Record confirmed predictions

When the user approves predictions, follow the tracking protocol in the project's
CLAUDE.md: upsert `predictions.json`, (re)generate the per-match report(s) under
`reports/`, regenerate `dashboard.html` (`scripts/generate_dashboard.py`, which scans
`reports/` and links each card to its match report — there is no `reports` array to
maintain). After matches finish, fill in
actual scores (`fetch_stats.py results`) and regenerate — the dashboard highlights
exact hits (green), correct outcomes (amber) and misses (red).

When the draw is the most likely outcome, the recommendation will be a draw scoreline
(1-1 or 0-0) — present it as such, never override toward a favorite. The EV logic goes
further: in tight low-scoring matches it can recommend 0-0 even when one side is a
slight favorite, because the favorite's win probability is spread across many scorelines
while the draw concentrates in one or two. When the recommended score's outcome differs
from the modal outcome, add one line explaining this — otherwise it looks like a bug.

## Scripts

| script | purpose |
|---|---|
| `scripts/predict_score.py` | odds → probabilities, scorelines, EV-optimal prediction (pure Python) |
| `scripts/fetch_stats.py` | team form / h2h / fixtures from football-data.org or api-football.com |
| `scripts/elo.py` | Elo ratings from full match history: favorite cross-check, no-odds fallback (`match` emits `--lambdas`), `backtest` |
| `scripts/generate_report.py` | predictions JSON → one self-contained HTML report per match (deterministic name in `reports/`) |

Elo context worth knowing: backtested on WC 2010–2022, the Elo favorite wins only ~56%
of matches (draws ~22%) — football is noisy, so present confidence honestly. Elo win
expectancy ignores draws and overshoots vs bookmakers at the extremes; when both exist,
trust odds, use Elo as a sanity cross-check (disagreement on the favorite = flag it).
During the tournament run `elo.py ratings --refresh` (the flag goes after the subcommand)
so group-stage results update the ratings.

## Caveats

- Knockout-stage odds price 90 minutes; predict the 90-minute score and say so.
- Odds drift; for matches days away, recommend re-running closer to the deadline.
