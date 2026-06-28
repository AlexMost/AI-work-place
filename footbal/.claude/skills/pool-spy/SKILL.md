---
name: pool-spy
description: Fetch every pool member's football-prediction scores from the closed voetbalpoule / footballpool (delta-n) site and render a static page — a list of matches, each linking to a per-match table of who predicted what. Use when the user wants to see friends' predictions, "хто що поставив", "що поставили інші", "прогнози друзів/пулу", "who predicted what", or mentions voetbalpoule / the prediction pool. Other members' picks are visible only after kickoff, so run during or after a match.
---

# pool-spy — who predicted what in the pool

The user competes with friends on `voetbalpoule.delta-n.nl` (backend
`footballpool-api-prd.azurewebsites.net`). The site hides other people's predictions
until a match kicks off; after kickoff they are public. This skill pulls every member's
visible predictions and renders a small static site published to GitHub Pages alongside
the rest of `footbal/`.

## Workflow

### 1. Get a fresh Bearer token

The API uses a short-lived (~10h) Azure B2C token, so it must be refreshed each session.
Ask the user to grab it from the browser:

> DevTools → Network → click any request to `footballpool-api-prd...` → copy the
> `Authorization` header value (the part **after** `Bearer `).

Accept it via `--token`, the `POOL_API_TOKEN` env var, or `footbal/.env`. On a stale
token the script exits with HTTP 401 and these same instructions.

### 2. Generate the pages

```bash
cd footbal
python3 .claude/skills/pool-spy/scripts/pool_spy.py --token <BEARER>
```

Writes `footbal/pool/index.html` + `pool/match-<id>.html` + `pool/standings.html`
(deterministic names → regen overwrites). By default only matches that have **already
started** are rendered (the only ones where everyone's picks are visible). Flags:

- `--all` — also render not-yet-started matches (your own pick only; others show «—»).
- `--match PAN-ENG` — render a single match by team codes.
- `--dump <file>` then `--input <file>` — save the assembled data and re-render offline
  (no token needed), useful for tweaking the HTML.
- `--pool-id` / `POOL_ID` — override the pool (default is the user's pool).

Open `pool/index.html` to check it: match list newest-first; click a match → table of all
members sorted by rank with their scores. Finished matches show the final score, a points
column, and colour-coded cells (green = exact, amber = right outcome, red = miss).

The header «🏁 гонка пулу →» links to `pool/standings.html` — a separate dark-neon **3D
three.js race** (auto-generated with the rest of the site) showing how every member's
cumulative match points evolved over each finished match: who led, who overtook whom.
Each player is a glowing runner whose distance = points; a synced 2D leaderboard shows
exact numbers and ▲/▼ rank moves, with a play/scrub transport along the timeline. It
falls back to the 2D leaderboard if WebGL is unavailable, and shows an empty-state until
the first match finishes. **Caveat:** the race sums per-match `pointsEarned` only — it
excludes bonus-question points (+10 each), so its totals can differ from the pool's
official standing (the page states this).

### 3. Publish (only on the user's go-ahead)

```bash
cd footbal && npm run publish-gh-pages
```

`build-site` copies `pool/` into `dist/` and `gh-pages` pushes it. Live at
`https://alexmost.github.io/AI-work-place/footbal/pool/`.

### Automated / unattended updates

`scripts/pool_auto.sh` runs this whole flow unattended: a cheap snapshot decides whether
match state changed since the last deploy, and only then does the full fetch + render
(`scripts/pool_auto.py`, which reuses `pool_spy.py`) + push of `footbal/pool` to
`gh-pages`. It's what the project's scheduled GitHub Actions and the `npm run pool-auto`
command both invoke — see `footbal/CLAUDE.md` for the CI/cron setup and local commands.

## Notes

- Others' predictions appear only after kickoff — running well before a match shows an
  almost-empty table. Mention this if the output looks sparse.
- Matches are keyed by the API's stable `matchId`, so no team-name normalization is
  needed (unlike `wc-predict`).
- The tournament is split into phases (`/api/tournament/phases`: Group Stage 1/2/3,
  knockouts). `user-predictions` returns only the **active** phase, so `collect()` loops
  every phase with matches (passing `phaseId`) to pull the whole tournament — otherwise
  the race/tables would show just the current matchday.
- Pure stdlib (`urllib`); no npm deps. The token is never written to git.

## Script

| script | purpose |
|---|---|
| `scripts/pool_spy.py` | fetch all members + predictions, render `pool/` static site: match list, per-match tables, and the `standings.html` 3D race (`build_timeline` + `render_standings`) |
