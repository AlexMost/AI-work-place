#!/usr/bin/env python3
"""Render match predictions as a single self-contained HTML report and open it in the browser.

Input: a JSON file with this shape (only "prediction" per match is required —
it is exactly the output of predict_score.py --json):

{
  "title": "World Cup — predictions",
  "subtitle": "matchday 1, June 11-14",
  "matches": [
    {
      "kickoff": "Jun 11, 21:00",
      "prediction": { ...predict_score.py --json output... },
      "stats": {
        "home_form": {"record": "6W-2D-2L", "results": ["W","W","D"], "avg_scored": 1.7, "avg_conceded": 0.9},
        "away_form": { ... same ... },
        "h2h": {"record": "1W-1D-0L", "lines": ["2017-11-13  Mexico 3-1 South Africa"]}
      },
      "notes": "free-text caveat shown on the card"
    }
  ]
}

Usage: generate_report.py --input data.json [--out report.html] [--no-open]
"""

import argparse
import html
import json
import os
import sys
import webbrowser
from datetime import datetime

TOSS_UP_THRESHOLD = 0.40  # no outcome reaches 40% -> flag the match as a coin flip

FORM_COLORS = {"W": "bg-emerald-500", "D": "bg-stone-400", "L": "bg-rose-500"}


def esc(s):
    return html.escape(str(s))


def pct(x):
    return f"{x * 100:.0f}%"


def form_chips(results):
    chips = "".join(
        f'<span class="inline-flex w-5 h-5 rounded items-center justify-center text-[10px] '
        f'font-bold text-white {FORM_COLORS.get(r, "bg-stone-300")}">{esc(r)}</span>'
        for r in results)
    return f'<span class="inline-flex gap-1">{chips}</span>'


def form_block(label, form):
    if not form:
        return ""
    return f"""
      <div class="flex items-center justify-between gap-2 text-sm">
        <span class="text-stone-500 truncate">{esc(label)}</span>
        <span class="flex items-center gap-2 shrink-0">{form_chips(form.get("results", []))}
          <span class="text-xs text-stone-500">{esc(form.get("record", ""))}
          · {form.get("avg_scored", "?")} gf / {form.get("avg_conceded", "?")} ga</span></span>
      </div>"""


def match_card(m):
    p = m["prediction"]
    home, away = p["home"], p["away"]
    probs = p.get("implied_probabilities") or p["model_outcome_probabilities"]
    ph, pd_, pa = probs["home"], probs["draw"], probs["away"]
    rec = p["recommendation"]
    xg = p["expected_goals"]

    toss_up = max(ph, pd_, pa) < TOSS_UP_THRESHOLD
    badge = ('<span class="text-[10px] uppercase tracking-wider bg-amber-100 text-amber-800 '
             'rounded-full px-2 py-0.5">toss-up — low confidence</span>') if toss_up else ""
    kickoff = f'<span class="text-xs text-stone-400">{esc(m["kickoff"])}</span>' if m.get("kickoff") else ""

    odds = p.get("odds")
    odds_line = (f'<div class="text-xs text-stone-400 mt-1">odds {odds["home"]} / {odds["draw"]} / '
                 f'{odds["away"]} · margin removed</div>') if odds else \
        '<div class="text-xs text-stone-400 mt-1">no odds — model built from team goal averages</div>'

    top = "".join(
        f'<span class="inline-flex items-baseline gap-1 bg-stone-100 rounded-lg px-2 py-1">'
        f'<span class="font-semibold">{esc(s["score"])}</span>'
        f'<span class="text-[10px] text-stone-500">{pct(s["probability"])}</span></span>'
        for s in p.get("top_scorelines", [])[:6])

    alts = " · ".join(f'{esc(a["score"])} (EV {a["expected_points"]:.2f})'
                      for a in p.get("alternatives", [])[:3])

    stats = m.get("stats") or {}
    h2h = stats.get("h2h") or {}
    h2h_html = ""
    if h2h.get("lines"):
        lines = "".join(f'<div class="text-xs text-stone-500">{esc(l)}</div>' for l in h2h["lines"][:5])
        h2h_html = f"""
      <div class="mt-3 pt-3 border-t border-stone-100">
        <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-1">head-to-head
          {(" · " + esc(h2h["record"])) if h2h.get("record") else ""}</div>{lines}
      </div>"""

    notes = (f'<div class="mt-3 text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">'
             f'{esc(m["notes"])}</div>') if m.get("notes") else ""

    return f"""
    <article class="bg-white rounded-2xl border border-stone-200 shadow-sm p-6">
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-lg font-semibold">{esc(home)} <span class="text-stone-400 font-normal">vs</span> {esc(away)}</h2>
        <div class="flex flex-col items-end gap-1">{kickoff}{badge}</div>
      </div>
      {odds_line}

      <div class="mt-4 flex h-2.5 rounded-full overflow-hidden">
        <div class="bg-emerald-500" style="width:{ph * 100:.1f}%"></div>
        <div class="bg-stone-300" style="width:{pd_ * 100:.1f}%"></div>
        <div class="bg-rose-400" style="width:{pa * 100:.1f}%"></div>
      </div>
      <div class="mt-1 flex justify-between text-xs text-stone-500">
        <span class="text-emerald-700">{esc(home)} {pct(ph)}</span>
        <span>draw {pct(pd_)}</span>
        <span class="text-rose-600">{esc(away)} {pct(pa)}</span>
      </div>

      <div class="mt-5 flex items-center gap-6">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-stone-400">prediction</div>
          <div class="text-4xl font-bold text-emerald-700 tabular-nums">{esc(rec["score"].replace("-", " : "))}</div>
          <div class="text-xs text-stone-500">P(exact) {pct(rec["probability"])} · EV {rec["expected_points"]:.2f} pts</div>
        </div>
        <div class="text-xs text-stone-500">
          <div class="text-[10px] uppercase tracking-wider text-stone-400">expected goals</div>
          <div class="tabular-nums">{xg["home"]:.2f} — {xg["away"]:.2f}</div>
          <div class="mt-1 text-[10px] uppercase tracking-wider text-stone-400">alternatives</div>
          <div>{alts or "—"}</div>
        </div>
      </div>

      <div class="mt-4">
        <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-1">most likely scorelines</div>
        <div class="flex flex-wrap gap-1.5">{top}</div>
      </div>

      <div class="mt-3 space-y-1">
        {form_block(f"{home} form", stats.get("home_form"))}
        {form_block(f"{away} form", stats.get("away_form"))}
      </div>
      {h2h_html}{notes}
    </article>"""


def render(data):
    cards = "\n".join(match_card(m) for m in data["matches"])
    subtitle = f'<p class="text-stone-500 mt-1">{esc(data["subtitle"])}</p>' if data.get("subtitle") else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(data.get("title", "Match predictions"))}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-50 text-slate-900">
<main class="max-w-5xl mx-auto px-6 py-12">
  <header class="mb-8">
    <div class="text-[10px] uppercase tracking-wider text-stone-400">wc-predict · poisson model on bookmaker odds</div>
    <h1 class="text-3xl font-bold" style="font-family: Georgia, 'Times New Roman', serif">{esc(data.get("title", "Match predictions"))}</h1>
    {subtitle}
  </header>
  <div class="grid md:grid-cols-2 gap-6">
{cards}
  </div>
  <footer class="mt-10 text-xs text-stone-400">
    Probabilities are de-margined bookmaker odds fitted to an independent-Poisson goals model.
    Even the best pick lands the exact score only ~10–17% of the time — that's football.
  </footer>
</main>
</body>
</html>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="path to the predictions JSON file")
    ap.add_argument("--out", help="output HTML path (default: temp dir)")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    if not data.get("matches"):
        sys.exit("error: input JSON has no matches")

    if args.out:
        out = args.out
    else:
        # keep reports inside the project (reports/) so the dashboard can link to them
        root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "..", "..", "..", ".."))
        out = os.path.join(root, "reports", f"wc-report-{datetime.now().strftime('%Y%m%d-%H%M')}.html")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data))
    print(f"report written: {out}")
    if not args.no_open:
        webbrowser.open(f"file://{os.path.abspath(out)}")


if __name__ == "__main__":
    main()
