# Getting 1X2 odds from favbet.hr

> Prefer `scripts/fetch_odds.py` (The Odds API, `ODDS_API_KEY` in .env) when available:
> the median of 10–25 bookmakers is more reliable than any single book, and it prints
> ready-to-run predict_score.py commands. Use favbet (below) as the fallback, or when
> the user wants the exact line their friends are looking at.

The user's bookmaker of reference. World Cup page:
`https://www.favbet.hr/en/sports/category/soccer/960/?timeFilter={"all":"all"}`
(category 960 = the World Cup tournament; the site is a JavaScript SPA).

Odds are decimal. The three numbers per match are 1X2: first team win / draw / second team win.
"Home" in our scripts = the first-listed team (World Cup venues are neutral, except hosts).

## Strategy, in order

### 1. Chrome DevTools MCP (preferred when available)

If the `chrome-devtools` MCP server is connected:

1. `new_page` → navigate to the URL above.
2. `wait_for` content (match rows render after JS loads; a couple of seconds).
3. `take_snapshot` and read the 1X2 odds for each match of interest from the
   accessibility tree. Match rows contain team names, kickoff time and three odds buttons.
4. If the snapshot is too noisy, `list_network_requests` after loading — the SPA fetches
   odds as JSON (look for XHR responses containing event/odds data). Reading that JSON via
   `get_network_request` is more reliable than parsing the DOM, and reveals an API URL
   that may be callable directly next time.

### 2. WebFetch (cheap to try, usually fails)

A plain fetch of the page typically returns the empty SPA shell. Try once; don't insist.

### 3. Ask the user (always works)

Ask the user to either paste the odds as text ("Mexico 1.65 / 3.6 / 5.5") or drop a
screenshot of the favbet page — odds are perfectly readable from screenshots.

## Caveats

- Never invent or "estimate" odds from memory: the whole model is garbage-in-garbage-out,
  and stale/imagined odds silently poison every downstream number. If odds can't be
  obtained, either use `--lambdas` from team stats (see stats-apis.md) or stop and ask.
- Odds drift over time. For best predictions fetch them close to the prediction deadline.
- If Over/Under 2.5 odds are visible, grab them too — they sharpen the total-goals
  estimate (`--over25` / `--under25` flags).
