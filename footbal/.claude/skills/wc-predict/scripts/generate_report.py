#!/usr/bin/env python3
"""Render match predictions as self-contained HTML reports — one file per match.

Each match is written to reports/wc-report-<date>-<home>-vs-<away>.html, a name derived
deterministically from (home, away, kickoff). Re-predicting a match overwrites its single
file instead of piling up timestamped duplicates.

The report shows the full reasoning of the prediction pipeline, not just the pick:
the de-margined odds, the fitted goals model (lambdas + Dixon-Coles rho), the full
scoreline heatmap, the expected-points ranking, the totals market, and a methodology
stepper. Everything past the stored prediction is RECOMPUTED at render time from
expected_goals + dixon_coles_rho by importing the model's pure functions — no extra
input fields are needed for the heatmap or the EV table.

Input: a JSON file with this shape (only "prediction" per match is required —
it is exactly the output of predict_score.py --json):

{
  "matches": [
    {
      "kickoff": "2026-06-11T19:00:00Z",          // ISO UTC; drives both the filename and the displayed time
      "prediction": { ...predict_score.py --json output... },
      "stats": {
        "home_form": {"record": "6W-2D-2L", "results": ["W","W","D"], "avg_scored": 1.7, "avg_conceded": 0.9},
        "away_form": { ... same ... },
        "h2h": {"record": "1W-1D-0L", "lines": ["2017-11-13  Mexico 3-1 South Africa"]}
      },
      "books": 24,                                 // optional: bookmaker count behind the consensus odds
      "analysis": ["free-text reasoning bullet", ...],  // optional: qualitative notes shown as a list
      "notes": "free-text caveat shown on the card"     // optional: single amber caveat box
    }
  ]
}

Usage: generate_report.py --input data.json [--out report.html] [--no-open]
  --out is honoured only when the input has exactly one match; otherwise each match
  gets its deterministic per-match filename under reports/.
"""

import argparse
import html
import json
import os
import re
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from team_names import report_filename  # noqa: E402
from predict_score import (  # noqa: E402
    score_matrix, outcome_of, demargin_power, ev_ranking, best_per_outcome,
    DEFAULT_RHO, MAX_GOALS, TABLE_MAX_GOALS, RESIDUAL_WARN,
)

TOSS_UP_THRESHOLD = 0.40  # no outcome reaches 40% -> flag the match as a coin flip
DEFAULT_SCORING = {"exact": 8, "outcome": 5}

FORM_COLORS = {"W": "bg-emerald-500", "D": "bg-stone-400", "L": "bg-rose-500"}

# outcome -> rgb triplet for heatmap shading and dots (emerald-500 / stone-500 / rose-500)
OUTCOME_RGB = {"home": "16,185,129", "draw": "120,113,108", "away": "244,63,94"}
OUTCOME_DOT = {"home": "bg-emerald-500", "draw": "bg-stone-400", "away": "bg-rose-400"}

TIER_CLS = {
    "emerald": "bg-emerald-50 text-emerald-700 border-emerald-200",
    "stone": "bg-stone-100 text-stone-600 border-stone-200",
    "amber": "bg-amber-50 text-amber-800 border-amber-200",
    "sky": "bg-sky-50 text-sky-700 border-sky-200",
}


def esc(s):
    return html.escape(str(s))


def pct(x):
    return f"{x * 100:.0f}%"


def pct1(x):
    return f"{x * 100:.1f}%"


def pp(delta):
    """Signed percentage-point delta, e.g. -0.7 п.п."""
    return f"{delta * 100:+.1f} п.п."


def fmt_kickoff(kickoff):
    """ISO '2026-06-11T19:00:00Z' -> '2026-06-11 19:00 UTC'; any other string shown verbatim."""
    if not kickoff:
        return ""
    s = str(kickoff)
    return f"{s[:16].replace('T', ' ')} UTC" if re.match(r"\d{4}-\d{2}-\d{2}T", s) else s


def outcome_label(outc, home, away):
    return {"home": f"перемога {home}", "away": f"перемога {away}", "draw": "нічия"}[outc]


def chip(text, tier="stone"):
    return (f'<span class="inline-flex items-center gap-1 text-[11px] rounded-full px-2.5 py-1 '
            f'border {TIER_CLS[tier]}">{esc(text)}</span>')


# ---------------------------------------------------------------------------
# derive: recompute the full model state from the stored prediction snapshot
# ---------------------------------------------------------------------------

def derive(p):
    """Recompute matrix, outcome probs, EV ranking and marginals from the stored
    expected_goals + dixon_coles_rho, so the report visualizes the model directly
    rather than the handful of fields predict_score chose to serialise."""
    xg = p["expected_goals"]
    lam_h, lam_a = xg["home"], xg["away"]
    rho = p.get("dixon_coles_rho", DEFAULT_RHO)
    matrix = score_matrix(lam_h, lam_a, rho, MAX_GOALS)

    home = draw = away = over25 = 0.0
    n = len(matrix)
    marg_home = [0.0] * n
    marg_away = [0.0] * n
    for i in range(n):
        for j in range(n):
            pij = matrix[i][j]
            marg_home[i] += pij
            marg_away[j] += pij
            if i > j:
                home += pij
            elif i == j:
                draw += pij
            else:
                away += pij
            if i + j >= 3:
                over25 += pij
    outcome = {"home": home, "draw": draw, "away": away, "over25": over25}

    scorelines = [(i, j, matrix[i][j])
                  for i in range(TABLE_MAX_GOALS + 1)
                  for j in range(TABLE_MAX_GOALS + 1)]
    scorelines.sort(key=lambda r: (-r[2], r[0] + r[1], abs(r[0] - r[1]), -r[0]))
    top5_mass = sum(pr for _, _, pr in scorelines[:5])
    top_cell = (scorelines[0][0], scorelines[0][1])

    scoring = p.get("scoring") or DEFAULT_SCORING
    pe, po = scoring["exact"], scoring["outcome"]
    outcome_p = {"home": home, "draw": draw, "away": away}
    ev = ev_ranking(matrix, outcome_p, pe, po)
    ev_rows = ev[:8]
    best_po = best_per_outcome(ev)

    ri, rj = (int(x) for x in p["recommendation"]["score"].split("-"))
    rec_cell = (ri, rj)

    # Grid grows to cover >=95% of probability (so blowout favourites with high lambda
    # don't render a misleadingly truncated map), but always shows every cell of interest.
    interest = ([top_cell, rec_cell] + [(i, j) for i, j, _, _ in ev_rows]
                + [tuple(int(x) for x in b["score"].split("-")) for b in best_po])
    G = max(5, max(max(i, j) for i, j in interest))
    while G < 9 and sum(matrix[i][j] for i in range(G + 1) for j in range(G + 1)) < 0.95:
        G += 1
    coverage = sum(matrix[i][j] for i in range(G + 1) for j in range(G + 1))

    d = {
        "matrix": matrix, "outcome": outcome, "marg_home": marg_home, "marg_away": marg_away,
        "scorelines": scorelines, "top5_mass": top5_mass, "top_cell": top_cell,
        "rec_cell": rec_cell, "ev_rows": ev_rows, "best_po": best_po,
        "scoring": scoring, "rho": rho,
        "G": G, "coverage": coverage, "total_xg": lam_h + lam_a,
        "raw_implied": None, "fair_probs": None, "fair_over": None,
    }

    odds = p.get("odds")
    if odds:
        inv = [1.0 / odds["home"], 1.0 / odds["draw"], 1.0 / odds["away"]]
        s = sum(inv)
        d["raw_implied"] = {"home": inv[0] / s, "draw": inv[1] / s, "away": inv[2] / s}
        fair = p.get("implied_probabilities")
        if not fair:
            fh, fd, fa = demargin_power([odds["home"], odds["draw"], odds["away"]])
            fair = {"home": fh, "draw": fd, "away": fa}
        d["fair_probs"] = fair

    ou = p.get("over_under_25_odds")
    if ou:
        d["fair_over"] = demargin_power([ou["over"], ou["under"]])[0]
    # derived (not read from the snapshot) so pre-fit_quality snapshots get it too
    d["fit_residual"] = (abs(outcome["over25"] - d["fair_over"])
                         if d["fair_over"] is not None else None)

    return d


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------

def section_header(m, p):
    home, away = p["home"], p["away"]
    d_out = m["_d"]["outcome"]
    toss_up = max(d_out["home"], d_out["draw"], d_out["away"]) < TOSS_UP_THRESHOLD
    badge = ('<span class="text-[10px] uppercase tracking-wider bg-amber-100 text-amber-800 '
             'rounded-full px-2 py-0.5">монетка — низька впевненість</span>') if toss_up else ""
    kickoff = (f'<span class="text-xs text-stone-400">{esc(fmt_kickoff(m["kickoff"]))}</span>'
               if m.get("kickoff") else "")
    return f"""
      <div class="flex items-start justify-between gap-2">
        <h2 class="text-2xl font-semibold">{esc(home)} <span class="text-stone-400 font-normal">проти</span> {esc(away)}</h2>
        <div class="flex flex-col items-end gap-1">{kickoff}{badge}</div>
      </div>"""


def why_line(p, d):
    rec, top = d["rec_cell"], d["top_cell"]
    home, away = p["home"], p["away"]
    if rec == top:
        return ("Рекомендований рахунок водночас і найімовірніший, "
                "і найкращий за очікуваними балами.")
    ti, tj = top
    ri, rj = rec
    p_top = d["matrix"][ti][tj]
    rec_outc = outcome_of(*rec)
    p_rec_outcome = d["outcome"][rec_outc]
    label = outcome_label(rec_outc, home, away)
    po = d["scoring"]["outcome"]
    return (f"{ti}-{tj} — найімовірніший окремий рахунок ({pct(p_top)}), але {ri}-{rj} дає більше "
            f"очікуваних балів: навіть неточний прогноз приносить {po:g} б. щоразу, коли "
            f"спрацьовує результат «{esc(label)}» ({pct(p_rec_outcome)}).")


def section_verdict(p, d):
    home, away = p["home"], p["away"]
    rec = p["recommendation"]
    xg = p["expected_goals"]
    o = d["outcome"]
    ph, pd_, pa = o["home"], o["draw"], o["away"]
    sc = d["scoring"]
    return f"""
    <section class="mt-5 bg-stone-50 rounded-2xl border border-stone-200 p-5">
      <div class="flex flex-wrap items-end gap-x-8 gap-y-3">
        <div>
          <div class="text-[10px] uppercase tracking-wider text-stone-400">прогноз</div>
          <div class="text-5xl font-bold text-emerald-700 tabular-nums">{esc(rec["score"].replace("-", " : "))}</div>
          <div class="text-xs text-stone-500 mt-1">P(точний) {pct(rec["probability"])} · очік. бали {rec["expected_points"]:.2f}
            <span class="text-stone-400">@ {sc["exact"]:g}/{sc["outcome"]:g}</span></div>
        </div>
        <div class="text-sm text-stone-500">
          <div class="text-[10px] uppercase tracking-wider text-stone-400">очікувані голи (λ)</div>
          <div class="tabular-nums text-lg text-stone-700">{xg["home"]:.2f} — {xg["away"]:.2f}</div>
        </div>
      </div>

      <div class="mt-4 flex h-2.5 rounded-full overflow-hidden">
        <div class="bg-emerald-500" style="width:{ph * 100:.1f}%"></div>
        <div class="bg-stone-300" style="width:{pd_ * 100:.1f}%"></div>
        <div class="bg-rose-400" style="width:{pa * 100:.1f}%"></div>
      </div>
      <div class="mt-1 flex justify-between text-xs text-stone-500">
        <span class="text-emerald-700">{esc(home)} {pct(ph)}</span>
        <span>нічия {pct(pd_)}</span>
        <span class="text-rose-600">{esc(away)} {pct(pa)}</span>
      </div>

      <p class="mt-4 text-sm text-stone-600">{why_line(p, d)}</p>
    </section>"""


def section_chips(m, p, d):
    chips = []

    mass = d["top5_mass"]
    if mass < 0.55:
        chips.append(chip(f"топ-5 рахунків — {pct(mass)} імовірності", "amber"))
    elif mass <= 0.80:
        chips.append(chip(f"топ-5 рахунків — {pct(mass)} імовірності", "stone"))
    else:
        chips.append(chip(f"топ-5 рахунків — {pct(mass)} імовірності", "sky"))

    mg = p.get("bookmaker_margin")
    if mg is not None:
        if mg < 0.045:
            chips.append(chip(f"маржа {pct1(mg)} · гостра лінія", "emerald"))
        elif mg <= 0.07:
            chips.append(chip(f"маржа {pct1(mg)} · типова", "stone"))
        else:
            chips.append(chip(f"маржа {pct1(mg)} · широка", "amber"))

    books = m.get("books") or p.get("books")
    if books:
        chips.append(chip(f"консенсус {books} букмекерів", "stone"))

    if p.get("over_under_25_odds"):
        chips.append(chip("ρ підігнано під ринок тоталів", "emerald"))
    else:
        chips.append(chip("ρ = історичний пріор", "stone"))

    conf = p.get("confidence")
    if conf and conf.get("grade"):
        tier = {"A": "emerald", "B": "stone", "C": "amber"}.get(conf["grade"], "stone")
        chips.append(chip(f"довіра {conf['grade']}", tier))

    fr = d.get("fit_residual")
    if fr is not None and fr > RESIDUAL_WARN:
        chips.append(chip(f"ρ не дотягнувся до тоталів · Δ {fr * 100:.1f} п.п.", "amber"))

    rho = d["rho"]
    if rho < -0.0005:
        rho_note = (f"ρ {rho:+.3f} — зміщує ймовірність у бік 0-0 та 1-1 і від 1-0/0-1: "
                    f"у футболі нічиї групуються на низьких рахунках.")
    elif rho > 0.0005:
        rho_note = f"ρ {rho:+.3f} — зміщує ймовірність від низьких нічийних рахунків."
    else:
        rho_note = "ρ 0 — без корекції низьких рахунків."

    return f"""
    <section class="mt-4">
      <div class="flex flex-wrap gap-1.5">{''.join(chips)}</div>
      <div class="mt-2 text-[11px] text-stone-400">
        у сучасних ЧС п'ять найчастіших рахунків покривають ~70% усіх матчів · {esc(rho_note)}
      </div>
    </section>"""


def section_analysis(m):
    bullets = m.get("analysis") or []
    if not bullets:
        return ""
    items = "".join(f'<li class="text-sm text-stone-600">{esc(b)}</li>' for b in bullets)
    return f"""
    <section class="mt-5">
      <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-2">аналіз</div>
      <ul class="list-disc list-outside pl-5 space-y-1">{items}</ul>
    </section>"""


def heat_cell(prob, i, j, p_max, rec, top):
    outc = outcome_of(i, j)
    a = (prob / p_max) ** 0.75 if p_max > 0 else 0.0
    if prob >= 0.001:
        a = max(a, 0.04)
    else:
        a = 0.0
    style = f"background:rgba({OUTCOME_RGB[outc]},{a:.3f})" if a > 0 else "background:#fff"
    txt = "text-white font-semibold" if a > 0.55 else "text-stone-700"
    if (i, j) == rec:
        style += ";box-shadow:inset 0 0 0 2px #047857"
    elif (i, j) == top:
        style += ";box-shadow:inset 0 0 0 2px #1c1917"
    label = pct(prob) if prob >= 0.005 else '<span class="text-stone-300">·</span>'
    return (f'<td class="text-center px-2 py-1.5 text-xs tabular-nums {txt}" '
            f'style="{style}">{label}</td>')


def section_heatmap(p, d):
    matrix = d["matrix"]
    G = d["G"]
    home, away = p["home"], p["away"]
    rec, top = d["rec_cell"], d["top_cell"]
    p_max = max(matrix[i][j] for i in range(G + 1) for j in range(G + 1))

    head = '<th class="px-1 py-1"></th>'
    head += "".join(f'<th class="px-2 py-1 text-[10px] text-stone-500 font-semibold tabular-nums">{j}</th>'
                    for j in range(G + 1))
    head += '<th class="px-2 py-1 text-[10px] text-stone-400 font-normal border-l border-stone-200">Σ</th>'
    rows = [f"<tr>{head}</tr>"]
    for i in range(G + 1):
        cells = f'<th class="px-2 py-1 text-[10px] text-stone-500 font-semibold tabular-nums text-right">{i}</th>'
        for j in range(G + 1):
            cells += heat_cell(matrix[i][j], i, j, p_max, rec, top)
        cells += (f'<td class="px-2 py-1 text-[10px] text-stone-400 tabular-nums text-center '
                  f'border-l border-stone-200">{pct(d["marg_home"][i])}</td>')
        rows.append(f"<tr>{cells}</tr>")
    foot = '<th class="px-1 py-1 border-t border-stone-200"></th>'
    for j in range(G + 1):
        foot += (f'<td class="px-2 py-1 text-[10px] text-stone-400 tabular-nums text-center '
                 f'border-t border-stone-200">{pct(d["marg_away"][j])}</td>')
    foot += '<td class="border-t border-l border-stone-200"></td>'
    rows.append(f"<tr>{foot}</tr>")

    return f"""
    <div class="bg-white rounded-2xl border border-stone-200 p-5">
      <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-1">матриця рахунків</div>
      <div class="text-[10px] text-stone-400 mb-3">{esc(home)} забиває ↓ · {esc(away)} забиває → ·
        сітка покриває {pct(d["coverage"])} імовірності (Σ — розподіл голів кожної команди)</div>
      <div class="overflow-x-auto">
        <table class="border-collapse">{''.join(rows)}</table>
      </div>
      <div class="mt-3 text-[10px] text-stone-400 flex flex-wrap gap-x-3 gap-y-1">
        <span><span class="inline-block w-2.5 h-2.5 align-middle" style="box-shadow:inset 0 0 0 2px #047857"></span> рекомендація</span>
        <span><span class="inline-block w-2.5 h-2.5 align-middle" style="box-shadow:inset 0 0 0 2px #1c1917"></span> найімовірніший</span>
        <span>відтінок = результат (перемога / нічия / поразка)</span>
      </div>
    </div>"""


def section_ev_table(p, d):
    rows = d["ev_rows"]
    sc = d["scoring"]
    pe, po = sc["exact"], sc["outcome"]
    ev_max = max((ev for *_, ev in rows), default=1.0) or 1.0
    rec = d["rec_cell"]
    o = d["outcome"]

    body = ""
    for n, (i, j, pr, ev) in enumerate(rows, 1):
        outc = outcome_of(i, j)
        p_out = o[outc]
        exact_pts = pr * pe
        outcome_pts = max(0.0, (p_out - pr) * po)
        w_e = exact_pts / ev_max * 100
        w_o = outcome_pts / ev_max * 100
        rowcls = "bg-emerald-50" if (i, j) == rec else ""
        body += f"""
        <tr class="{rowcls} border-t border-stone-100">
          <td class="px-2 py-1.5 text-stone-400 text-xs">{n}</td>
          <td class="px-2 py-1.5 font-semibold tabular-nums">{i}-{j}</td>
          <td class="px-2 py-1.5"><span class="inline-block w-2 h-2 rounded-full {OUTCOME_DOT[outc]}"></span></td>
          <td class="px-2 py-1.5 text-xs tabular-nums text-stone-600 text-right">{pct(pr)}</td>
          <td class="px-2 py-1.5 text-xs tabular-nums text-stone-600 text-right">{pct(p_out)}</td>
          <td class="px-2 py-1.5">
            <div class="flex items-center gap-2">
              <div class="flex h-2 rounded-full overflow-hidden bg-stone-100 grow min-w-[36px]">
                <div class="bg-emerald-600" style="width:{w_e:.1f}%"></div>
                <div class="bg-emerald-200" style="width:{w_o:.1f}%"></div>
              </div>
              <span class="text-xs tabular-nums font-medium w-9 text-right shrink-0">{ev:.2f}</span>
            </div>
          </td>
        </tr>"""

    home, away = p["home"], p["away"]
    hedge_rows = ""
    for b in d["best_po"]:
        is_top = b["ev_drop"] <= 0.0005
        drop = '<span class="text-stone-300">—</span>' if is_top else f'<span class="text-amber-700">−{b["ev_drop"]:.2f}</span>'
        hedge_rows += f"""
        <div class="flex items-center gap-2 text-sm">
          <span class="inline-block w-2 h-2 rounded-full shrink-0 {OUTCOME_DOT[b["outcome"]]}"></span>
          <span class="text-stone-600 grow truncate">{esc(outcome_label(b["outcome"], home, away))}</span>
          <span class="font-semibold tabular-nums">{esc(b["score"])}</span>
          <span class="text-xs tabular-nums text-stone-500 w-14 text-right">EV {b["expected_points"]:.2f}</span>
          <span class="text-xs tabular-nums w-12 text-right">{drop}</span>
        </div>"""

    return f"""
    <div class="bg-white rounded-2xl border border-stone-200 p-5">
      <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-3">кандидати за очікуваними балами</div>
      <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="text-[10px] uppercase tracking-wider text-stone-400 text-left">
            <th class="px-2 py-1 font-normal">№</th>
            <th class="px-2 py-1 font-normal">рахунок</th>
            <th class="px-2 py-1 font-normal">рез.</th>
            <th class="px-2 py-1 font-normal text-right">P(точн.)</th>
            <th class="px-2 py-1 font-normal text-right">P(рез.)</th>
            <th class="px-2 py-1 font-normal">очік. бали</th>
          </tr>
        </thead>
        <tbody>{body}</tbody>
      </table>
      </div>
      <div class="mt-4 pt-3 border-t border-stone-100">
        <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-2">найкращий рахунок у кожному результаті · ціна хеджу</div>
        <div class="space-y-1">{hedge_rows}</div>
        <div class="mt-2 text-[10px] text-stone-400">
          ціна хеджу = EV(топ-ставки) − EV(найкращого рахунку цього результату) · бали групової шкали, у плей-оф усе ×2
        </div>
      </div>
      <div class="mt-3 text-[10px] text-stone-400 flex flex-wrap gap-x-3 gap-y-1">
        <span><span class="inline-block w-2.5 h-2 rounded-sm bg-emerald-600 align-middle"></span> бали за точний рахунок</span>
        <span><span class="inline-block w-2.5 h-2 rounded-sm bg-emerald-200 align-middle"></span> бали за вгаданий результат</span>
      </div>
      <div class="mt-1 text-[10px] text-stone-400">
        EV = {pe:g} × P(точний) + {po:g} × (P(результат) − P(точний)) · пул: {pe:g}/{po:g} груповий, ×2 у плей-оф (те саме співвідношення)
      </div>
    </div>"""


def section_totals(p, d):
    over = d["outcome"]["over25"]
    under = 1.0 - over
    ou = p.get("over_under_25_odds")
    if ou and d["fair_over"] is not None:
        fair_over = d["fair_over"]
        market = (f'ринок {ou["over"]} / {ou["under"]} → чесний P(понад) {pct(fair_over)} · '
                  f'модель {pp(over - fair_over)} проти ринку')
    else:
        market = "тоталів на ринку немає — понад/менше з підігнаної моделі"
    return f"""
    <section class="mt-5 bg-white rounded-2xl border border-stone-200 p-5">
      <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-2">тотал голів</div>
      <div class="flex h-2.5 rounded-full overflow-hidden">
        <div class="bg-sky-500" style="width:{over * 100:.1f}%"></div>
        <div class="bg-stone-300" style="width:{under * 100:.1f}%"></div>
      </div>
      <div class="mt-1 flex justify-between text-xs text-stone-500">
        <span class="text-sky-700">понад 2.5 — {pct(over)}</span>
        <span>менше — {pct(under)}</span>
      </div>
      <div class="mt-2 text-xs text-stone-500">сумарний xG {d["total_xg"]:.2f} · {esc(market)}</div>
    </section>"""


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
          · {form.get("avg_scored", "?")} заб / {form.get("avg_conceded", "?")} проп</span></span>
      </div>"""


def section_context(m, p):
    home, away = p["home"], p["away"]
    stats = m.get("stats") or {}
    forms = form_block(f"форма {home}", stats.get("home_form")) + \
        form_block(f"форма {away}", stats.get("away_form"))

    h2h = stats.get("h2h") or {}
    h2h_html = ""
    if h2h.get("lines"):
        lines = "".join(f'<div class="text-xs text-stone-500">{esc(l)}</div>' for l in h2h["lines"][:5])
        h2h_html = f"""
      <div class="mt-3 pt-3 border-t border-stone-100">
        <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-1">очні зустрічі
          {(" · " + esc(h2h["record"])) if h2h.get("record") else ""}</div>{lines}
      </div>"""

    notes = (f'<div class="mt-3 text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2">'
             f'{esc(m["notes"])}</div>') if m.get("notes") else ""

    if not (forms or h2h_html or notes):
        return ""
    return f"""
    <section class="mt-5 bg-white rounded-2xl border border-stone-200 p-5">
      <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-2">контекст</div>
      <div class="space-y-1">{forms}</div>
      {h2h_html}{notes}
    </section>"""


def step_card(n, title, body):
    return f"""
      <div class="bg-white rounded-xl border border-stone-200 p-3">
        <div class="flex items-center gap-2 mb-2">
          <span class="inline-flex w-5 h-5 rounded-full bg-stone-900 text-white text-[10px] items-center justify-center font-bold">{n}</span>
          <span class="text-[10px] uppercase tracking-wider text-stone-400">{esc(title)}</span>
        </div>
        {body}
      </div>"""


def section_pipeline(m, p, d):
    home, away = p["home"], p["away"]
    odds = p.get("odds")
    o = d["outcome"]
    rho = d["rho"]
    books = m.get("books") or p.get("books")

    if not odds:
        market_steps = step_card(
            "1·2", "без ринкових коефіцієнтів",
            '<div class="text-xs text-stone-500">λ оцінено із середніх голів команд, '
            'а не з коефіцієнтів — крок зняття маржі не застосовний.</div>')
    else:
        mg = p.get("bookmaker_margin")
        bits = [f'<div class="text-sm tabular-nums text-stone-700">{odds["home"]} / {odds["draw"]} / {odds["away"]}</div>']
        meta = []
        if mg is not None:
            meta.append(f"маржа {pct1(mg)}")
        if books:
            meta.append(f"{books} букмекерів")
        ou = p.get("over_under_25_odds")
        if ou:
            meta.append(f"тотал {ou['over']} / {ou['under']}")
        if meta:
            bits.append(f'<div class="text-[10px] text-stone-400 mt-1">{esc(" · ".join(meta))}</div>')
        step1 = step_card("1", "ринкові коефіцієнти", "".join(bits))

        raw, fair = d["raw_implied"], d["fair_probs"]
        rows = "".join(
            f'<div class="flex items-center justify-between gap-2">'
            f'<span class="inline-block w-2 h-2 rounded-full shrink-0 {OUTCOME_DOT[k]}"></span>'
            f'<span class="tabular-nums text-stone-600">{pct1(raw[k])} → {pct1(fair[k])} '
            f'<span class="text-stone-400">({pp(fair[k] - raw[k])})</span></span></div>'
            for k in ("home", "draw", "away"))
        step2 = step_card(
            "2", "зняття маржі (power-метод)",
            f'<div class="text-xs space-y-1">{rows}</div>'
            '<div class="text-[10px] text-stone-400 mt-2">точки — перемога/нічия/поразка; '
            'аутсайдерів ріжуть сильніше за фаворитів.</div>')
        market_steps = step1 + step2

    calib = ('<span class="text-[10px] text-emerald-700">підігнано під ринок тоталів</span>'
             if p.get("over_under_25_odds") else
             '<span class="text-[10px] text-stone-400">історичний пріор</span>')
    step3 = step_card(
        "3", "фіт моделі голів",
        f'<div class="text-sm tabular-nums text-stone-700">λ {p["expected_goals"]["home"]:.2f} — {p["expected_goals"]["away"]:.2f}</div>'
        f'<div class="text-xs tabular-nums text-stone-500 mt-1">ρ {rho:+.3f} · {calib}</div>'
        '<div class="text-[10px] text-stone-400 mt-2">дві λ підібрано так, щоб модельні W/D/W '
        'точно збіглися з чесними коефіцієнтами.</div>')

    check = ""
    if d["fair_probs"]:
        max_dev = max(abs(o[k] - d["fair_probs"][k]) for k in ("home", "draw", "away"))
        if max_dev < 0.005:
            check = '<div class="text-[10px] text-emerald-700 mt-2">✓ збігається з чесними коефіцієнтами</div>'
    step4 = step_card(
        "4", "модельні ймовірності",
        f'<div class="text-xs space-y-0.5 text-stone-600">'
        f'<div class="flex justify-between"><span>{esc(home)}</span><span class="tabular-nums">{pct1(o["home"])}</span></div>'
        f'<div class="flex justify-between"><span>нічия</span><span class="tabular-nums">{pct1(o["draw"])}</span></div>'
        f'<div class="flex justify-between"><span>{esc(away)}</span><span class="tabular-nums">{pct1(o["away"])}</span></div>'
        f'<div class="flex justify-between border-t border-stone-100 pt-0.5"><span>понад 2.5</span><span class="tabular-nums">{pct1(o["over25"])}</span></div>'
        f'</div>{check}')

    return f"""
    <section class="mt-5">
      <div class="text-[10px] uppercase tracking-wider text-stone-400 mb-2">як модель дійшла до цього</div>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3">{market_steps}{step3}{step4}</div>
    </section>"""


def match_page(m):
    p = m["prediction"]
    m["_d"] = derive(p)
    d = m["_d"]
    # wide grids (blowout favourites, high lambda) overflow a half-width card -> stack full-width
    evidence_cls = "grid grid-cols-1 gap-5" if d["G"] >= 7 else "grid grid-cols-1 md:grid-cols-2 gap-5"
    return f"""
    <article class="bg-white rounded-2xl border border-stone-200 shadow-sm p-6">
      {section_header(m, p)}
      {section_verdict(p, d)}
      {section_chips(m, p, d)}
      {section_analysis(m)}
      <section class="mt-5 {evidence_cls}">
        {section_heatmap(p, d)}
        {section_ev_table(p, d)}
      </section>
      {section_totals(p, d)}
      {section_context(m, p)}
      {section_pipeline(m, p, d)}
    </article>"""


def render(data):
    cards = "\n".join(match_page(m) for m in data["matches"])
    subtitle = f'<p class="text-stone-500 mt-1">{esc(data["subtitle"])}</p>' if data.get("subtitle") else ""
    return f"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(data.get("title", "Прогнози матчів"))}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-stone-50 text-slate-900">
<main class="max-w-4xl mx-auto px-6 py-12">
  <header class="mb-8">
    <div class="text-[10px] uppercase tracking-wider text-stone-400">wc-predict · модель Пуассона на коефіцієнтах букмекерів</div>
    <h1 class="text-3xl font-bold" style="font-family: Georgia, 'Times New Roman', serif">{esc(data.get("title", "Прогнози матчів"))}</h1>
    {subtitle}
  </header>
  <div class="space-y-8">
{cards}
  </div>
  <footer class="mt-10 text-xs text-stone-400">
    Ймовірності — це коефіцієнти букмекерів зі знятою маржею, підігнані під незалежну модель голів Пуассона.
    Навіть найкращий пік влучає у точний рахунок лише ~10–17% разів — це футбол.
    Пік обирається за очікуваними балами (EV), а не за найімовірнішим рахунком, тож може відрізнятися від модального.
  </footer>
</main>
</body>
</html>"""


def match_report_data(m):
    """Wrap one match in the single-match render() shape, titled by the fixture."""
    p = m["prediction"]
    title = f'{p["home"]} проти {p["away"]}'
    return {"title": title, "subtitle": fmt_kickoff(m.get("kickoff")), "matches": [m]}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="path to the predictions JSON file")
    ap.add_argument("--out", help="output HTML path; only valid when the input has exactly one match")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    matches = data.get("matches")
    if not matches:
        sys.exit("error: input JSON has no matches")
    if args.out and len(matches) != 1:
        sys.exit("error: --out is only valid for a single-match input; "
                 f"got {len(matches)} matches (each gets its own deterministic filename)")

    reports_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..", "..", "..", "reports"))
    written = []
    for m in matches:
        p = m["prediction"]
        out = args.out or os.path.join(reports_dir, report_filename(p["home"], p["away"], m.get("kickoff")))
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(render(match_report_data(m)))
        written.append(out)
        print(f"report written: {out}")

    # one match -> open it; many -> don't spam tabs (the dashboard links them all)
    if not args.no_open and len(written) == 1:
        webbrowser.open(f"file://{os.path.abspath(written[0])}")


if __name__ == "__main__":
    main()
