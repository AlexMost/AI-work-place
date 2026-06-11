#!/usr/bin/env python3
"""Render the prediction-tracking dashboard from the predictions ledger.

Ledger (predictions.json) shape:
{
  "title": "ЧС-2026 — трекер прогнозів",
  "scoring": {"exact": 8, "outcome": 5},            // group base; playoff is doubled (x2)
  "predictions": [
    {
      "home": "Mexico", "away": "South Africa",
      "kickoff": "2026-06-11T19:00:00Z",            // optional, UTC
      "stage": "group",                              // "group" (default) | "playoff"
                                                     //   (or a knockout name) -> points x2
      "predicted": [2, 1],                           // what the user entered on their site
      "model": {                                     // optional: the FULL `predict_score.py
        "recommendation": {"score": "1-0", ...},     //   --json` snapshot, stored verbatim so
        "implied_probabilities": {...},              //   the pick stays reproducible (includes
        "expected_goals": {...}, "fit_quality": {...},//  odds, dixon_coles_rho, confidence,
        ...                                          //   best_per_outcome, ...)
      },                                             // legacy compact form (recommended [1,0],
                                                     //   probs {...}, odds [..]) still accepted
                                                     //   — model_view() normalizes both
      "actual": [3, 1],                              // null until the match is played (90' score)
      "note": ""                                     // optional
    }
  ],
  "bonus_questions": [                               // optional, +10 each
    {"q": "...", "answer": "...", "confidence": "...", "basis": "...",
     "correct": null}                                // true / false / null (unresolved)
  ]
}

The dashboard is regenerated in full every time — never edit index.html by hand.
(The file is named index.html so GitHub Pages serves it at the directory root and
back-links from methodology.html work the same locally and in prod.)

Each prediction card links to its per-match report (reports/wc-report-<date>-<home>-vs-<away>.html,
named by team_names.report_filename) whenever that file exists on disk — so the report list is
derived from the predictions, never a hand-maintained array that can drift or duplicate.

Usage: generate_dashboard.py [--ledger predictions.json] [--out index.html]
                             [--fixtures fixtures.json] [--no-open]
With --fixtures (output of `fetch_stats.py fixtures --json`) the dashboard also shows a
coverage section: upcoming matches with no prediction yet (guaranteed zeros otherwise).
Default paths resolve relative to the project root (two dirs above .claude/).
"""

import argparse
import html
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from team_names import normalize, report_filename  # noqa: E402

DEFAULT_SCORING = {"exact": 8, "outcome": 5}  # pool rules (CLAUDE.md); group base
BONUS_POINTS = 10                              # per correct bonus question
COVERAGE_WINDOW_DAYS = 4                        # flag unpredicted fixtures kicking off within N days


def esc(s):
    return html.escape(str(s))


def outcome(score):
    h, a = score
    return "home" if h > a else ("away" if a > h else "draw")


def model_view(m):
    """Normalized view over both `model` shapes the ledger has accumulated: the
    canonical full predict_score --json snapshot (recommendation {"score": "1-0"},
    model_outcome_probabilities) and the older compact form (recommended [1, 0],
    probs). Returns {"rec": [h, a] | None, "probs": dict | None, "grade": str | None}."""
    if not m:
        return {"rec": None, "probs": None, "grade": None}
    rec = m.get("recommended")
    if rec is None and isinstance(m.get("recommendation"), dict):
        score = str(m["recommendation"].get("score") or "")
        parts = score.split("-", 1)
        if len(parts) == 2 and all(x.isdigit() for x in parts):
            rec = [int(x) for x in parts]
    probs = (m.get("probs") or m.get("model_outcome_probabilities")
             or m.get("implied_probabilities"))
    conf = m.get("confidence")
    grade = conf.get("grade") if isinstance(conf, dict) else None
    return {"rec": rec, "probs": probs, "grade": grade}


def stage_mult(stage):
    """Playoff matches are worth double (16/10 vs 8/5); group is the default x1."""
    return 2 if (stage and str(stage).lower() != "group") else 1


def score_entry(pred, actual, scoring, stage="group"):
    """(points, status_key) for a prediction. Both None until the match is played.

    status_key is one of exact/outcome/miss and is derived directly (not by comparing
    points to a threshold) so playoff doubling can never be mistaken for a different tier.
    """
    if actual is None or pred is None:
        return None, None
    mult = stage_mult(stage)
    if list(pred) == list(actual):
        return scoring["exact"] * mult, "exact"
    if outcome(pred) == outcome(actual):
        return scoring["outcome"] * mult, "outcome"
    return 0, "miss"


STATUS = {
    None: ("pending", "border-stone-200 bg-white", "очікує", "bg-stone-100 text-stone-500"),
    "exact": ("exact", "border-emerald-300 bg-emerald-50", "точний рахунок", "bg-emerald-600 text-white"),
    "outcome": ("outcome", "border-amber-300 bg-amber-50", "вгадано переможця", "bg-amber-500 text-white"),
    "miss": ("miss", "border-rose-200 bg-rose-50", "мимо", "bg-rose-500 text-white"),
}


def is_overdue(p):
    """Kickoff is in the past but no actual recorded yet — needs filling/attention."""
    if p.get("actual") or not p.get("kickoff"):
        return False
    try:
        ko = datetime.fromisoformat(str(p["kickoff"]).replace("Z", "+00:00"))
    except ValueError:
        return False
    return ko < datetime.now(timezone.utc)


def card(p, scoring, report_href=None):
    stage = p.get("stage", "group")
    pred, actual = p.get("predicted"), p.get("actual")
    pts, key = score_entry(pred, actual, scoring, stage)
    _, card_cls, label, badge_cls = STATUS[key]
    overdue = is_overdue(p)
    if overdue:
        card_cls = "border-rose-300 bg-rose-50/40"
    pts_txt = "" if pts is None else f" · +{pts}"

    stage_badge = ('<span class="shrink-0 text-[10px] uppercase tracking-wider rounded-full '
                   'px-2 py-0.5 bg-indigo-100 text-indigo-700">плей-оф ×2</span>'
                   if stage_mult(stage) == 2 else "")

    kickoff = ""
    if p.get("kickoff"):
        kickoff = f'<div class="text-xs text-stone-400">{esc(p["kickoff"][:16].replace("T", " "))} UTC</div>'
    overdue_html = ('<div class="text-xs font-semibold text-rose-600 mt-1">⚠ матч зіграно — '
                    'впиши фактичний рахунок</div>' if overdue else "")

    pred_txt = f'{pred[0]} : {pred[1]}' if pred else "— : —"
    actual_txt = f'{actual[0]} : {actual[1]}' if actual else "— : —"
    model_html = ""
    m = p.get("model")
    if m:
        mv = model_view(m)
        rec, probs = mv["rec"], mv["probs"]
        mpts, _ = score_entry(rec, actual, scoring, stage)
        agree = rec and pred and list(rec) == list(pred)
        rec_txt = f'{rec[0]}:{rec[1]}' if rec else "?"
        prob_txt = (f' · {probs["home"]:.0%}/{probs["draw"]:.0%}/{probs["away"]:.0%}' if probs else "")
        mark = "" if mpts is None else f' → +{mpts}'
        grade_txt = f' · довіра {mv["grade"]}' if mv["grade"] else ""
        diverged = " (ти зіграв інакше)" if (rec and pred and not agree) else ""
        model_html = (f'<div class="mt-2 text-xs text-stone-500">модель: {rec_txt}'
                      f'{diverged}{prob_txt}{mark}{grade_txt}</div>')

    note = f'<div class="mt-1 text-xs text-stone-400 italic">{esc(p["note"])}</div>' if p.get("note") else ""

    title_inner = (f'{esc(p.get("home", "?"))} <span class="text-stone-400 font-normal">vs</span> '
                   f'{esc(p.get("away", "?"))}')
    title_html = (f'<a class="font-semibold hover:text-emerald-600" href="{esc(report_href)}" '
                  f'title="відкрити звіт">{title_inner}</a>'
                  if report_href else f'<div class="font-semibold">{title_inner}</div>')

    return f"""
    <article class="rounded-2xl border {card_cls} p-5">
      <div class="flex items-start justify-between gap-2">
        {title_html}
        <div class="flex flex-col items-end gap-1">
          <span class="shrink-0 text-[10px] uppercase tracking-wider rounded-full px-2 py-0.5 {badge_cls}">{label}{pts_txt}</span>
          {stage_badge}
        </div>
      </div>
      {kickoff}{overdue_html}
      <div class="mt-3 flex items-center gap-6">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-stone-400">прогноз</div>
          <div class="text-3xl font-bold tabular-nums {'text-stone-300' if not pred else ''}">{pred_txt}</div>
        </div>
        <div>
          <div class="text-[10px] uppercase tracking-wider text-stone-400">факт</div>
          <div class="text-3xl font-bold tabular-nums {'text-stone-300' if not actual else ''}">{actual_txt}</div>
        </div>
      </div>
      {model_html}{note}
    </article>"""


def tile(value, label, accent=""):
    return (f'<div class="bg-white rounded-2xl border border-stone-200 p-5 text-center">'
            f'<div class="text-3xl font-bold tabular-nums {accent}">{value}</div>'
            f'<div class="text-[10px] uppercase tracking-wider text-stone-400 mt-1">{label}</div></div>')


def bonus_section(bonus, scoring):
    if not bonus:
        return "", 0
    earned = 0
    rows = []
    for b in bonus:
        correct = b.get("correct")
        if correct is True:
            earned += BONUS_POINTS
            badge = f'<span class="text-[10px] rounded-full px-2 py-0.5 bg-emerald-600 text-white">+{BONUS_POINTS}</span>'
        elif correct is False:
            badge = '<span class="text-[10px] rounded-full px-2 py-0.5 bg-rose-500 text-white">мимо</span>'
        else:
            badge = '<span class="text-[10px] rounded-full px-2 py-0.5 bg-stone-100 text-stone-500">очікує</span>'
        conf = f' · {esc(b["confidence"])}' if b.get("confidence") else ""
        rows.append(
            f'<div class="bg-white rounded-xl border border-stone-200 px-4 py-3">'
            f'<div class="flex items-start justify-between gap-2">'
            f'<div class="text-sm font-medium">{esc(b.get("q", ""))}</div>{badge}</div>'
            f'<div class="text-sm text-emerald-700 font-semibold mt-1">{esc(b.get("answer", ""))}'
            f'<span class="text-xs text-stone-400 font-normal">{conf}</span></div>'
            + (f'<div class="text-xs text-stone-400 mt-1">{esc(b["basis"])}</div>' if b.get("basis") else "")
            + '</div>')
    head = (f'<div class="text-[10px] uppercase tracking-wider text-stone-400 mb-2">'
            f'бонусні питання · +{BONUS_POINTS} за кожне · набрано {earned}</div>')
    return (f'<section class="mb-8">{head}<div class="grid md:grid-cols-2 gap-3">'
            f'{"".join(rows)}</div></section>'), earned


def coverage_section(preds, fixtures):
    """Upcoming fixtures with no prediction in the ledger — guaranteed zeros otherwise."""
    if not fixtures:
        return ""
    have = {frozenset((normalize(p.get("home")), normalize(p.get("away")))) for p in preds}
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=COVERAGE_WINDOW_DAYS)
    missing = []
    for f in fixtures:
        h, a = f.get("home"), f.get("away")
        if not h or not a or h == "TBD" or a == "TBD":
            continue
        if frozenset((normalize(h), normalize(a))) in have:
            continue
        ko = f.get("date") or ""
        try:
            when = datetime.fromisoformat(str(ko).replace("Z", "+00:00"))
            if when < now or when > horizon:
                continue  # already played, or too far out to act on yet
        except ValueError:
            continue  # no usable kickoff -> can't place it in the window
        missing.append((ko, h, a, f.get("group") or f.get("stage") or ""))
    if not missing:
        return ""
    missing.sort(key=lambda r: r[0])
    rows = "".join(
        f'<div class="flex items-center justify-between bg-white rounded-xl border border-amber-300 px-4 py-2 text-sm">'
        f'<span>{esc(h)} <span class="text-stone-400">vs</span> {esc(a)}'
        f'{(" · " + esc(g)) if g else ""}</span>'
        f'<span class="text-xs text-stone-400">{esc(ko[:16].replace("T", " "))}</span></div>'
        for ko, h, a, g in missing)
    return (f'<section class="mb-8"><div class="text-[10px] uppercase tracking-wider text-amber-700 '
            f'mb-2">⚠ матчі без прогнозу ({len(missing)}) — кожен пропуск = гарантований 0</div>'
            f'<div class="grid md:grid-cols-2 gap-2">{rows}</div></section>')


def render(data, fixtures=None, reports_dir=None):
    scoring = data.get("scoring", DEFAULT_SCORING)
    have_report = set(os.listdir(reports_dir)) if reports_dir and os.path.isdir(reports_dir) else set()
    preds = sorted(data["predictions"], key=lambda p: p.get("kickoff") or "9999")
    finished = [p for p in preds if p.get("actual") and p.get("predicted")]
    scored = [score_entry(p["predicted"], p["actual"], scoring, p.get("stage", "group"))
              for p in finished]
    my = [pts for pts, _ in scored]
    model_recs = [(p, model_view(p.get("model"))["rec"]) for p in finished]
    model = [score_entry(rec, p["actual"], scoring, p.get("stage", "group"))[0]
             for p, rec in model_recs if rec]
    n_exact = sum(1 for _, k in scored if k == "exact")
    n_out = sum(1 for _, k in scored if k == "outcome")
    overdue_n = sum(1 for p in preds if is_overdue(p))

    bonus_html, bonus_pts = bonus_section(data.get("bonus_questions", []), scoring)

    tiles = [
        tile(sum(my) + bonus_pts, "мої бали", "text-emerald-700"),
        tile(sum(model) if model else "—", "бали моделі", "text-stone-600"),
        tile(f"{n_exact}/{len(finished)}" if finished else "0/0", "точні рахунки"),
        tile(f"{n_exact + n_out}/{len(finished)}" if finished else "0/0", "вгаданий результат"),
        tile(len(preds) - len(finished), "очікують гри",
             "text-rose-600" if overdue_n else ""),
    ]
    cov_html = coverage_section(preds, fixtures)

    def report_href(p):
        fn = report_filename(p.get("home"), p.get("away"), p.get("kickoff"))
        return f"reports/{fn}" if fn in have_report else None

    cards = "\n".join(card(p, scoring, report_href(p)) for p in preds)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    bonus_note = f" · бонуси +{bonus_pts}" if bonus_pts else ""
    return f"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(data.get("title", "Трекер прогнозів"))}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-50 text-slate-900">
<main class="max-w-5xl mx-auto px-6 py-12">
  <header class="mb-8">
    <div class="text-[10px] uppercase tracking-wider text-stone-400">wc-predict · оновлено {stamp}</div>
    <div class="flex items-end justify-between gap-4">
      <h1 class="text-3xl font-bold" style="font-family: Georgia, 'Times New Roman', serif">{esc(data.get("title", "Трекер прогнозів"))}</h1>
      <a href="methodology.html" class="text-xs text-emerald-700 hover:underline whitespace-nowrap">як модель рахує →</a>
    </div>
  </header>
  <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">{''.join(tiles)}</div>
  {cov_html}
  {bonus_html}
  <div class="grid md:grid-cols-2 gap-5">
{cards}
  </div>
  <footer class="mt-10 text-xs text-stone-400">
    {scoring["exact"]}/{scoring["outcome"]} бали за точний рахунок / вгаданий результат
    (плей-оф ×2: {scoring["exact"] * 2}/{scoring["outcome"] * 2}){bonus_note} ·
    «бали моделі» — якби завжди грати рекомендацію моделі
  </footer>
</main>
</body>
</html>"""


def main():
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "..", ".."))
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ledger", default=os.path.join(root, "predictions.json"))
    ap.add_argument("--out", default=os.path.join(root, "index.html"))
    ap.add_argument("--fixtures", help="fetch_stats.py fixtures --json output, for the coverage section")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    try:
        with open(args.ledger, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        sys.exit(f"error: ledger not found: {args.ledger}")

    fixtures = None
    if args.fixtures:
        with open(args.fixtures, encoding="utf-8") as f:
            fixtures = json.load(f)

    reports_dir = os.path.join(os.path.dirname(os.path.abspath(args.out)), "reports")
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(data, fixtures, reports_dir))
    print(f"dashboard written: {args.out}")
    if not args.no_open:
        webbrowser.open(f"file://{os.path.abspath(args.out)}")


if __name__ == "__main__":
    main()
