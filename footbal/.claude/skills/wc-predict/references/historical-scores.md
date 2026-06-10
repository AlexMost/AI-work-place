# Historical scorelines — sanity check (data through 2025)

Computed from the open dataset of international results
(github.com/martj42/international_results, retrieved June 2026). Scores are
winner-loser ordered (1-0 includes 0-1); knockout scores include extra time.

## World Cup finals tournaments

| Score | All-time 1930–2022 (964 m.) | Modern era 1990–2022 (552 m.) |
|---|---|---|
| 1-0 | 18.9% | 21.6% |
| 2-1 | 15.8% | 17.8% |
| 2-0 | 11.5% | 12.7% |
| 1-1 | 9.5% | 10.5% |
| 0-0 | 8.1% | 8.0% |
| 3-0 | 5.9% | 6.0% |
| 3-1 | 7.1% | 5.4% |
| 2-2 | 3.6% | 4.3% |
| 3-2 | 4.5% | 3.8% |
| 4-1 | 3.2% | 2.5% |
| 4-0 | 2.5% | 2.4% |

Top-5 scores (1-0, 2-1, 2-0, 1-1, 0-0) cover **70%** of all modern-era matches.

## Modern priors (WC 1990+, confirmed by WC+Euro+Copa América 2014–2025, 489 m.)

- Average total goals per match: **~2.5** (lambda ~1.25 per team for equal sides).
- Draw rate: **~24%**.
- **76–78%** of matches have 3 or fewer total goals.
- Blowouts are rare even for huge favorites: 4-0 or heavier is ~5% of matches.
  Favorites win 1-0 / 2-0 / 2-1 far more often than 4-0.
- The 2014–2025 major-tournament distribution (latest: Euro 2024, Copa América 2024)
  is almost identical to the WC modern era — scoring patterns are stable, so these
  priors transfer directly to WC 2026.

## How to use this

After running the Poisson model, glance at its top scorelines. They should look like the
tables above: 1-0, 2-1, 2-0, 1-1 territory. If the model recommends something exotic
(4-2, 3-3 — each under ~2% historically), the odds input is probably wrong (typo, wrong
match, odds for a different market) — re-check before presenting.

For toss-up matches, 1-1 is a strong pick: draws are ~24% of matches, and 1-1 alone is
~10% — the second most common exact score in modern World Cups.
