# Football predictions — World Cup 2026

Score predictions for a friendly game (the user competes with friends on a prediction
site). The prediction pipeline lives in the `wc-predict` skill
(`.claude/skills/wc-predict/SKILL.md`).

## Pool rules (fixed 2026-06-10, from the organizers)

- Group stage: **8 points** exact score; **5 points** correct outcome (winner or draw)
  without exact score; 0 otherwise.
- Playoff: everything doubled — **16 / 10**. The result counts **after 90 minutes**
  (extra time and shootouts are ignored), so a draw is a valid playoff prediction.
- Bonus questions: +10 each; deadline June 11, 21:00.
- Predictions editable until 15 minutes before kickoff. Points update nightly.
- Strategy implication: at an 8:5 ratio the EV is dominated by the outcome term —
  generally play the most probable outcome's most probable scoreline. Playoff doubling
  keeps the ratio, so per-match logic is identical; bonus questions are worth ~1.25
  exact group hits each.

## Files

- `predictions.json` — the ledger, single source of truth for all tracked predictions
- `dashboard.html` — rendered tracker; NEVER edit by hand, always regenerate
- `reports/` — per-matchday HTML prediction reports, linked from the dashboard
- `.env` — API keys (FOOTBALL_DATA_TOKEN, API_FOOTBALL_KEY, ODDS_API_KEY)

## Prediction-tracking protocol

1. **When the user confirms a prediction** — says «ок», «беру», «ставлю 2-1», or
   otherwise approves a score for a match — upsert an entry in `predictions.json`
   (identify a match by `(home, away, kickoff date)`, not names alone — group opponents
   can meet again in the knockouts; update in place if re-predicted before the deadline):
   - `predicted` = the score the user actually puts on their site. A bare «ок» /
     «беру» after a model run means "I'm playing the model's recommendation" —
     set `predicted` = `model.recommended` without asking again. Only if the user
     names a different score («ставлю 2-1») does `predicted` differ from the model.
   - `model` = full `predict_score.py --json` snapshot (`recommended, probs, odds`, plus
     `over25/under25, lambdas, rho` when present) so the pick stays reproducible — recorded
     automatically every time predictions are generated, never asked from the user.
   - `stage` = `"playoff"` for any knockout match (scored ×2 = 16/10); omit or `"group"`
     otherwise.
   Then regenerate: `python3 .claude/skills/wc-predict/scripts/generate_dashboard.py`

2. **When generating a prediction report**, write it to `reports/` (descriptive name,
   e.g. `wc-report-matchday2.html`), append it to the `reports` array in the ledger,
   and regenerate the dashboard so it's linked.

3. **When matches have been played** (user asks to update, or a new session starts
   mid-tournament): fetch finished scores —
   `python3 .claude/skills/wc-predict/scripts/fetch_stats.py results --json` —
   fill `actual: [h, a]` for matching ledger entries, regenerate the dashboard, and
   tell the user the points earned. The script already returns the **90-minute** score
   (extra time and shootouts excluded) plus `duration`/`stage`, matching the pool rule.
   Match team names loosely: sources disagree (Czechia vs Czech Republic,
   Bosnia-Herzegovina vs Bosnia and Herzegovina) — `scripts/team_names.py` normalizes them.

4. **Coverage check** (every dashboard regen, and always when a session starts
   mid-tournament): make sure no upcoming match is missing a prediction — a forgotten
   match is a guaranteed 0. Pass the fixtures feed to the dashboard to surface gaps:
   `fetch_stats.py fixtures --limit 200 --json > /tmp/fixtures.json` then
   `generate_dashboard.py --fixtures /tmp/fixtures.json`. The dashboard also flags
   overdue entries (kickoff passed, no `actual` yet).

5. The ledger schema is documented in the docstring of
   `.claude/skills/wc-predict/scripts/generate_dashboard.py` (it includes `stage`,
   `bonus_questions`, and the 8/5 scoring; playoff is doubled in code, not in the ledger).
