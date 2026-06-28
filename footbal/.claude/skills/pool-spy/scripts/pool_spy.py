#!/usr/bin/env python3
"""Fetch every pool member's predictions from the voetbalpoule / footballpool API and
render a small static site: a list of matches, each linking to a per-match page that
shows what every participant predicted (like the screenshot the user shared).

The pool site hides other people's predictions until a match kicks off, so only matches
that have already started carry everyone's scores — those are the ones rendered by
default. Run this during or after kickoff.

Auth: the API uses a short-lived (~10h) Azure B2C Bearer token. Grab a fresh one from the
browser (DevTools -> Network -> any request to footballpool-api-prd -> Authorization
header) and pass it via --token, the POOL_API_TOKEN env var, or .env.

Output: writes <footbal>/pool/index.html + pool/match-<id>.html, published to GitHub
Pages by the footbal `npm run publish-gh-pages` flow. Pure Python 3, no dependencies.
"""

import argparse
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API_BASE = "https://footballpool-api-prd.azurewebsites.net"
DEFAULT_POOL_ID = "5211d7bd-4040-4826-8157-647bd5c99a6a"
ORIGIN = "https://voetbalpoule.delta-n.nl"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# scripts -> pool-spy -> skills -> .claude -> footbal
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))
DEFAULT_OUT = os.path.join(PROJECT_ROOT, "pool")


def load_dotenv():
    """Load the nearest .env (cwd upwards, then this script's dir upwards).

    Real environment variables always win; the first .env found is used.
    """
    candidates = []
    for start in (os.getcwd(), SCRIPT_DIR):
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


def api_get(path, params, token):
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/json, text/plain, */*",
        "Authorization": f"Bearer {token}",
        "Origin": ORIGIN,
        "Referer": ORIGIN + "/",
        "content-type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            sys.exit(
                f"error: API rejected the token (HTTP {e.code}). The Bearer token is "
                "short-lived (~10h) — grab a fresh one from the browser:\n"
                "  DevTools -> Network -> any request to footballpool-api-prd -> "
                "copy the Authorization header value (after 'Bearer ').\n"
                "Then re-run with --token <token> (or set POOL_API_TOKEN in .env)."
            )
        if e.code == 429:
            sys.exit("error: rate limited (HTTP 429). Wait a moment and retry.")
        sys.exit(f"error: HTTP {e.code} for {url}: {e.read().decode()[:300]}")
    except urllib.error.URLError as e:
        sys.exit(f"error: cannot reach the API ({e.reason}). Check your connection.")


def fetch_participants(token, pool_id):
    """All members of the pool, paginated."""
    out = []
    offset = 0
    page_size = 50
    while True:
        body = api_get(f"/api/pool/participants/{pool_id}",
                       {"offSet": offset, "pageSize": page_size}, token)
        out.extend(body.get("data", []))
        pg = body.get("pagination", {})
        if not pg.get("hasNextPage"):
            break
        offset += page_size
    return out


def fetch_phases(token):
    """All tournament phases (Group Stage 1/2/3, knockouts). Predictions are queried
    per phase — `user-predictions` defaults to the active phase only, so iterating phases
    is the only way to pull the whole tournament (every played matchday)."""
    body = api_get("/api/tournament/phases", {}, token)
    return body.get("data", []) or []


def fetch_user_predictions(token, user_id, pool_id, phase_id=None):
    """One member's visible predictions for a phase; tolerate non-sharers (empty)."""
    params = {"userId": user_id, "poolId": pool_id}
    if phase_id:
        params["phaseId"] = phase_id
    body = api_get("/api/prediction/user-predictions", params, token)
    return body.get("data", []) or []


def collect(token, pool_id):
    """Return (participants, matches_by_id, preds) where preds[matchId][userId] = entry.

    Walks every phase that has matches (G1/G2/G3 + any started knockout round) so the
    ledger spans the full tournament, not just the active matchday.
    """
    participants = fetch_participants(token, pool_id)
    phase_objs = fetch_phases(token)
    phase_ids = [ph.get("id") for ph in phase_objs
                 if ph.get("id") and (ph.get("matchCount") or 0) > 0] or [None]
    matches = {}   # matchId -> match metadata
    preds = {}     # matchId -> { userId -> {"goals":(h,a), "points":int|None} }
    for p in participants:
        uid = p["id"]
        if not p.get("allowPredictionSharing", True):
            continue
        for phase_id in phase_ids:
            for entry in fetch_user_predictions(token, uid, pool_id, phase_id):
                m = entry.get("match") or {}
                mid = m.get("matchId")
                if not mid:
                    continue
                matches.setdefault(mid, m)
                pred = entry.get("prediction") or {}
                if pred.get("homeGoals") is None or pred.get("awayGoals") is None:
                    continue
                preds.setdefault(mid, {})[uid] = {
                    "goals": (pred["homeGoals"], pred["awayGoals"]),
                    "points": pred.get("pointsEarned"),
                }
    return participants, matches, preds, phase_objs


# --- match helpers ---------------------------------------------------------

def is_finished(m):
    return m.get("status") == "MATCH_FINISHED"


def has_started(m):
    ts = m.get("timeStamp")
    if ts:
        return ts <= time.time()
    return is_finished(m)


def actual_score(m):
    # Only finished matches carry a real result; NOT_STARTED reports 0:0, live is partial.
    if not is_finished(m):
        return None
    h, a = m.get("homeGoals"), m.get("awayGoals")
    if h is None or a is None or h < 0 or a < 0:
        return None
    return (h, a)


def code(m, side):
    c = (m.get(f"{side}TeamCode") or "")[:3].upper()
    return c or (m.get(f"{side}TeamName") or "?")[:3].upper()


def match_label(m):
    return f"{code(m, 'home')} – {code(m, 'away')}"


def fmt_date(m):
    sd = m.get("startDate")
    if not sd:
        return ""
    try:
        dt = datetime.fromisoformat(sd.replace("Z", ""))
        return dt.strftime("%d.%m %H:%M")
    except ValueError:
        return sd


def status_badge(m):
    if is_finished(m):
        return ("завершено", "bg-slate-200 text-slate-700")
    if has_started(m):
        return ("live", "bg-rose-100 text-rose-700")
    return ("не почався", "bg-amber-100 text-amber-700")


def outcome_class(pred_goals, actual):
    """Tailwind classes for a predicted cell given the real result (or None)."""
    if actual is None:
        return ""
    ph, pa = pred_goals
    ah, aa = actual
    if ph == ah and pa == aa:
        return "bg-emerald-100 text-emerald-800 font-bold"            # exact
    if (ph - pa > 0) == (ah - aa > 0) and (ph - pa < 0) == (ah - aa < 0):
        return "bg-amber-100 text-amber-800"                          # right outcome
    return "bg-rose-50 text-rose-700"                                 # miss


def esc(s):
    return html.escape(str(s))


# --- standings timeline ----------------------------------------------------

# Neon palette for the 3D race runners (cyan/magenta family, like the 2048 game).
NEON_PALETTE = [
    "#34e1ff", "#ff4ed5", "#9b8cff", "#4ade80", "#fbbf24",
    "#f87171", "#22d3ee", "#a3e635", "#fb923c", "#e879f9",
    "#60a5fa", "#f472b6", "#2dd4bf", "#facc15", "#c084fc",
]


def short_name(display):
    """First token of the display name — tight enough for a 3D label."""
    n = (display or "").strip()
    return n.split()[0] if n else "?"


def build_timeline(participants, matches, preds, phases=None):
    """Cumulative match-points standings after each finished match, chronologically.

    Returns {"players":[...], "steps":[...], "maxTotal":int, "bands":[...]} where bands
    are coloured stretches of the track, one per phase, spanning the pool's average
    cumulative points from the phase's start to its end.
    Only players who share predictions are included (matches the rest of the site).
    NOTE: per-match `points` excludes bonus-question points, so totals here are the
    match-points race, not necessarily the pool's official standing.
    """
    pred_uids = set()
    for users in preds.values():
        pred_uids.update(users.keys())
    players = [p for p in participants
               if p.get("allowPredictionSharing", True) and p["id"] in pred_uids]
    players.sort(key=lambda x: x.get("rank", 999))

    finished = [(mid, m) for mid, m in matches.items() if is_finished(m)]
    finished.sort(key=lambda kv: kv[1].get("timeStamp", 0))

    cumulative = {p["id"]: 0 for p in players}
    steps = []
    for mid, m in finished:
        pfm = preds.get(mid, {})
        for p in players:
            pr = pfm.get(p["id"])
            pts = pr.get("points") if pr else None
            cumulative[p["id"]] += pts or 0
        totals = dict(cumulative)
        order = sorted(players, key=lambda p: (-totals[p["id"]], p.get("rank", 999)))
        act = actual_score(m)
        steps.append({
            "label": match_label(m),
            "home": m.get("homeTeamName", ""),
            "away": m.get("awayTeamName", ""),
            "date": fmt_date(m),
            "score": f"{act[0]}:{act[1]}" if act else "",
            "totals": totals,
            "ranks": [p["id"] for p in order],
            "phaseId": m.get("phaseId"),
        })

    players_out = [{"id": p["id"], "name": short_name(p.get("displayName")),
                    "full": p.get("displayName", ""),
                    "color": NEON_PALETTE[i % len(NEON_PALETTE)]}
                   for i, p in enumerate(players)]
    max_total = max((max(s["totals"].values()) for s in steps), default=0)

    # coloured track zones, one per phase (boundary = pool's avg total at phase end)
    BAND_COLORS = ["#34e1ff", "#ff4ed5", "#fbbf24", "#9b8cff", "#4ade80", "#f87171"]
    phase_meta = {ph["id"]: ph for ph in (phases or []) if ph.get("id")}
    bands = []
    if phase_meta and steps:
        # boundary = top score at each phase end, so the last zone reaches the finish
        seen, top_at_end = [], {}
        for st in steps:
            pid = st.get("phaseId")
            if pid not in seen:
                seen.append(pid)
            vals = list(st["totals"].values())
            top_at_end[pid] = max(vals) if vals else 0
        prev = 0.0
        for idx, pid in enumerate(seen):
            top = top_at_end[pid]
            bands.append({
                "label": phase_short(phase_meta.get(pid)) or "—",
                "color": BAND_COLORS[idx % len(BAND_COLORS)],
                "from": round(prev, 1), "to": round(top, 1),
            })
            prev = top
        bands[-1]["to"] = max_total  # last zone always reaches the finish (no gap)

    return {"players": players_out, "steps": steps, "maxTotal": max_total, "bands": bands}


# --- rendering -------------------------------------------------------------

HEAD = """<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-900">
<main class="max-w-3xl mx-auto px-4 py-8">
"""

FOOT = """
</main>
</body>
</html>
"""


PHASE_LABEL_UK = {
    "G1": "Груповий етап · 1-й тур", "G2": "Груповий етап · 2-й тур",
    "G3": "Груповий етап · 3-й тур", "16F": "1/16 фіналу", "8F": "1/8 фіналу",
    "QF": "1/4 фіналу", "SF": "1/2 фіналу", "F": "Фінал", "TF": "Матч за 3-тє місце",
}


def phase_label(meta):
    if not meta:
        return None
    return PHASE_LABEL_UK.get(meta.get("code")) or meta.get("name") or "Матчі"


PHASE_SHORT = {
    "G1": "GROUP 1", "G2": "GROUP 2", "G3": "GROUP 3", "16F": "R32", "8F": "R16",
    "QF": "QF", "SF": "SF", "F": "FINAL", "TF": "3RD PLACE",
}


def phase_short(meta):
    if not meta:
        return None
    return PHASE_SHORT.get(meta.get("code")) or meta.get("code") or "—"


def _index_row(m, n_pred, fname):
    label, label_cls = status_badge(m)
    act = actual_score(m)
    score_txt = f'{act[0]}:{act[1]}' if act else "—"
    return f"""
  <a href="{esc(fname)}" class="block bg-white rounded-xl shadow-sm hover:shadow-md
     ring-1 ring-slate-200 transition px-5 py-4 flex items-center gap-4">
    <div class="text-xs text-slate-400 w-20 shrink-0">{esc(fmt_date(m))}</div>
    <div class="flex-1 min-w-0">
      <div class="font-semibold tracking-wide">{esc(match_label(m))}</div>
      <div class="text-sm text-slate-500 truncate">{esc(m.get('homeTeamName',''))} —
        {esc(m.get('awayTeamName',''))}</div>
    </div>
    <div class="text-lg font-bold tabular-nums w-12 text-center">{esc(score_txt)}</div>
    <span class="text-[11px] px-2 py-0.5 rounded-full {label_cls}">{esc(label)}</span>
    <div class="text-xs text-slate-400 w-16 text-right shrink-0">{n_pred} прог.</div>
  </a>"""


def render_index(groups, generated_at):
    """groups: list of (label_or_None, [(match, n_predictions, filename), ...]).
    A None label renders an unheaded section (used when phases are unavailable)."""
    sections = []
    for label, items in groups:
        if not items:
            continue
        rows = "\n".join(_index_row(m, n, fn) for m, n, fn in items)
        head = ""
        if label:
            head = (f'<h2 class="text-xs font-semibold uppercase tracking-wider '
                    f'text-slate-400 mt-7 mb-2 first:mt-0">{esc(label)} '
                    f'<span class="text-slate-300">· {len(items)}</span></h2>')
        sections.append(head + f'\n  <div class="space-y-2.5">{rows}\n  </div>')
    body = "\n".join(sections) or (
        '<p class="text-slate-500">Поки немає матчів, що стартували — прогнози інших '
        'видно лише після кікофу. Запусти під час або після старту матчу.</p>')
    return HEAD.format(title="Прогнози пулу — хто що поставив") + f"""
  <header class="mb-6">
    <div class="flex items-start justify-between gap-3">
      <h1 class="text-2xl font-bold">Прогнози пулу</h1>
      <a href="standings.html" class="shrink-0 text-sm font-semibold px-3 py-1.5 rounded-full
         text-white bg-gradient-to-r from-cyan-500 to-fuchsia-500 hover:opacity-90
         shadow-sm whitespace-nowrap">🏁 гонка пулу →</a>
    </div>
    <p class="text-slate-500 text-sm mt-1">Хто що поставив, по фазах турніру. Натисни
       матч, щоб побачити прогнози всіх учасників.</p>
  </header>
{body}
  <p class="text-xs text-slate-400 mt-8">оновлено {esc(generated_at)}</p>
""" + FOOT


def render_match(m, participants, preds_for_match):
    act = actual_score(m)
    label, label_cls = status_badge(m)
    score_block = ""
    if act:
        score_block = (f'<div class="text-3xl font-black tabular-nums mt-1">'
                       f'{act[0]} : {act[1]}</div>')
    rows = []
    for p in sorted(participants, key=lambda x: x.get("rank", 999)):
        pr = preds_for_match.get(p["id"])
        if pr:
            ph, pa = pr["goals"]
            cell_cls = outcome_class(pr["goals"], act)
            pred_txt = f"{ph}:{pa}"
            pts = pr.get("points")
            pts_txt = "" if (act is None or pts is None) else str(pts)
        else:
            cell_cls = "text-slate-300"
            pred_txt = "—"
            pts_txt = ""
        rows.append(f"""
    <tr class="border-t border-slate-100">
      <td class="px-4 py-2.5 font-medium">{esc(p.get('displayName',''))}</td>
      <td class="px-4 py-2.5 text-center tabular-nums rounded {cell_cls}">{esc(pred_txt)}</td>
      <td class="px-4 py-2.5 text-center text-slate-500 tabular-nums">{esc(pts_txt)}</td>
    </tr>""")
    table = "".join(rows)
    pts_header = "Бали" if act else ""
    return HEAD.format(title=match_label(m)) + f"""
  <a href="index.html" class="text-sm text-slate-500 hover:text-slate-800">← усі матчі</a>
  <header class="mt-3 mb-5 text-center">
    <div class="text-xs text-slate-400">{esc(fmt_date(m))} ·
       <span class="px-2 py-0.5 rounded-full {label_cls}">{esc(label)}</span></div>
    <h1 class="text-2xl font-bold mt-2">{esc(m.get('homeTeamName',''))} —
       {esc(m.get('awayTeamName',''))}</h1>
    {score_block}
  </header>
  <div class="bg-white rounded-xl ring-1 ring-slate-200 overflow-hidden">
    <table class="w-full text-sm">
      <thead>
        <tr class="bg-[#1b2545] text-white text-left">
          <th class="px-4 py-3 font-semibold">Учасник</th>
          <th class="px-4 py-3 font-semibold text-center">Прогноз</th>
          <th class="px-4 py-3 font-semibold text-center">{pts_header}</th>
        </tr>
      </thead>
      <tbody>{table}
      </tbody>
    </table>
  </div>
""" + FOOT


STANDINGS_TEMPLATE = r"""<!doctype html>
<html lang="uk">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#070b18">
<title>Гонка пулу — хто кого обганяв</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root{
    --bg-0:#070b18; --bg-1:#0d1326;
    --glass:rgba(22,30,55,.55); --glass-border:rgba(125,160,255,.18);
    --text:#eaf0ff; --text-dim:#8a96bf; --cyan:#34e1ff; --magenta:#ff4ed5;
  }
  *{box-sizing:border-box}
  html,body{margin:0;height:100%}
  body{
    font-family:"Space Grotesk",system-ui,-apple-system,sans-serif;
    color:var(--text); background-color:var(--bg-0);
    background:
      radial-gradient(120% 80% at 15% 0%, rgba(52,225,255,.18), transparent 60%),
      radial-gradient(120% 80% at 100% 100%, rgba(255,78,213,.16), transparent 55%),
      linear-gradient(160deg,var(--bg-1),var(--bg-0));
    background-color:var(--bg-0);
    overflow:hidden;
  }
  #scene{position:fixed; inset:0; z-index:0}
  .hud{position:fixed; z-index:2; pointer-events:none}
  .hud a,.hud button,.hud input{pointer-events:auto}
  /* top bar */
  #top{top:0; left:0; right:0; padding:14px 18px;
       display:flex; align-items:flex-start; justify-content:space-between; gap:12px}
  .back{font-size:12px; color:var(--text-dim); text-decoration:none}
  .back:hover{color:var(--text)}
  .title{
    font-weight:700; font-size:clamp(15px,2.3vw,20px); letter-spacing:.02em;
    background:linear-gradient(120deg,var(--cyan),#9b8cff 55%,var(--magenta));
    -webkit-background-clip:text; background-clip:text; color:transparent;
    filter:drop-shadow(0 0 14px rgba(52,225,255,.35));
  }
  .sub{font-size:11px; color:var(--text-dim); margin-top:2px}
  /* now-playing match banner (centered, updates as the race steps) */
  #nowplaying{
    top:56px; left:50%; transform:translateX(-50%);
    display:flex; align-items:baseline; gap:9px; justify-content:center; white-space:nowrap;
    max-width:94vw; padding:8px 18px; border-radius:999px;
    background:var(--glass); border:1px solid var(--glass-border); backdrop-filter:blur(8px);
  }
  #nowplaying.flash{animation:npflash .6s ease}
  @keyframes npflash{
    0%{box-shadow:0 0 0 rgba(52,225,255,0); border-color:var(--glass-border)}
    30%{box-shadow:0 0 26px rgba(52,225,255,.55); border-color:var(--cyan)}
    100%{box-shadow:0 0 0 rgba(52,225,255,0); border-color:var(--glass-border)}
  }
  .np-step{font-size:10.5px; color:var(--text-dim); letter-spacing:.10em; text-transform:uppercase}
  .np-sep{color:var(--text-dim); opacity:.5}
  .np-label{font-weight:700; font-size:clamp(15px,2.4vw,20px); letter-spacing:.03em}
  .np-score{font-variant-numeric:tabular-nums; font-weight:700; color:var(--cyan)}
  .np-teams{font-size:12px; color:var(--text-dim)}
  .np-date{font-size:12px; color:var(--text-dim)}
  /* leaderboard */
  #board{
    left:18px; top:104px; width:min(40vw,300px);
    background:var(--glass); border:1px solid var(--glass-border);
    border-radius:14px; padding:10px 12px; backdrop-filter:blur(8px);
  }
  #board h2{margin:0 0 8px; font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--text-dim); font-weight:600;
            display:flex; align-items:center; justify-content:space-between; gap:8px; cursor:pointer; user-select:none}
  #board h2 .chev{font-size:10px; opacity:.8}
  #board.collapsed{padding-bottom:10px; width:auto; max-height:none; overflow:visible}
  #board.collapsed #rows{display:none}
  #board.collapsed h2{margin-bottom:0}
  .row{display:flex; align-items:center; gap:8px; padding:4px 2px; font-size:14px}
  .row .pos{width:18px; text-align:right; color:var(--text-dim); font-variant-numeric:tabular-nums}
  .row .dot{width:10px; height:10px; border-radius:50%; flex:0 0 auto; box-shadow:0 0 8px currentColor}
  .row .nm{flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .row .pts{font-variant-numeric:tabular-nums; font-weight:700}
  .row .arr{width:14px; text-align:center; font-size:11px}
  .arr.up{color:#4ade80} .arr.down{color:#f87171} .arr.same{color:var(--text-dim)}
  .row.lead .nm{font-weight:700}
  /* controls */
  #ctl{
    left:50%; transform:translateX(-50%); bottom:18px; width:min(92vw,640px);
    background:var(--glass); border:1px solid var(--glass-border);
    border-radius:16px; padding:12px 16px; backdrop-filter:blur(8px);
    display:flex; align-items:center; gap:12px;
  }
  #play{
    width:42px; height:42px; flex:0 0 auto; border-radius:50%; cursor:pointer;
    border:1px solid var(--glass-border); background:rgba(52,225,255,.12);
    color:var(--text); font-size:16px; display:flex; align-items:center; justify-content:center;
  }
  #play:hover{background:rgba(52,225,255,.22)}
  #scrub{flex:1; accent-color:var(--cyan); cursor:pointer}
  #speed{
    flex:0 0 auto; cursor:pointer; font:inherit; font-size:12px; color:var(--text);
    background:rgba(125,160,255,.10); border:1px solid var(--glass-border);
    border-radius:10px; padding:6px 10px;
  }
  #stepno{flex:0 0 auto; font-size:12px; color:var(--text-dim); font-variant-numeric:tabular-nums; min-width:54px; text-align:right}
  /* empty / error overlay */
  #msg{
    position:fixed; inset:0; z-index:3; display:none; align-items:center; justify-content:center;
    text-align:center; padding:24px;
  }
  #msg div{max-width:420px; color:var(--text-dim); font-size:15px; line-height:1.5}
  #msg b{color:var(--text)}
  .note{position:fixed; z-index:2; bottom:74px; left:50%; transform:translateX(-50%);
        font-size:10.5px; color:var(--text-dim); opacity:.8; text-align:center; width:90vw}
  @media (max-width:640px){
    #board{width:min(56vw,220px); top:120px; max-height:54vh; overflow:auto; padding:8px 10px}
    #board h2{margin-bottom:5px}
    #board .row{font-size:12.5px; padding:2px 2px; gap:6px}
    #board .row .pos{width:14px}
    .np-teams{display:none}
  }
</style>
</head>
<body>
<canvas id="scene"></canvas>

<div class="hud" id="top">
  <div>
    <a class="back" href="index.html">&larr; усі матчі</a>
    <div class="title">Гонка пулу — хто кого обганяв</div>
    <div class="sub">кумулятивні бали за матчі · оновлено __GENERATED__</div>
  </div>
</div>

<div class="hud" id="nowplaying">
  <span class="np-step" id="np-step"></span>
  <span class="np-sep">·</span>
  <span class="np-label" id="np-label">—</span>
  <span class="np-score" id="np-score"></span>
  <span class="np-teams" id="np-teams"></span>
  <span class="np-date" id="np-date"></span>
</div>

<div class="hud" id="board">
  <h2 id="boardToggle">Таблиця <span class="chev" id="boardChev">▾</span></h2>
  <div id="rows"></div>
</div>

<div class="note">бали за матчі без бонус-питань (+10 кожне) — підсумок може відрізнятись від офіційного рейтингу пулу</div>

<div class="hud" id="ctl">
  <button id="play" title="Програти">▶</button>
  <input id="scrub" type="range" min="0" max="0" step="0.001" value="0">
  <button id="speed" title="Швидкість">4×</button>
  <div id="stepno">0/0</div>
</div>

<div id="msg"><div></div></div>

<script type="application/json" id="data">__DATA__</script>

<script type="importmap">
{ "imports": {
  "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
  "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
} }
</script>

<script>
// ---- shared state + 2D HUD (works even if WebGL/three fails to load) --------
const DATA = JSON.parse(document.getElementById('data').textContent);
const PLAYERS = DATA.players, STEPS = DATA.steps, MAXT = Math.max(DATA.maxTotal, 1);
const NSTEP = STEPS.length;
const byId = Object.fromEntries(PLAYERS.map(p => [p.id, p]));

const TRACK_LEN = 60, LANE_GAP = 3.2;
const laneZ = i => (i - (PLAYERS.length - 1) / 2) * LANE_GAP;
const laneIndex = Object.fromEntries(PLAYERS.map((p, i) => [p.id, i])); // fixed lane per player
const xOf = pts => (pts / MAXT) * TRACK_LEN;

let cur = 0;        // integer step index we are heading toward
let prog = 1;       // 0..1 interpolation from step cur-1 to cur
let playing = false;
const SPEEDS = [4, 2, 1, 0.5];
let speedIdx = 0;
const STEP_MS = 1400; // base duration per match at 1×

const totalsAt = i => (i < 0 ? Object.fromEntries(PLAYERS.map(p => [p.id, 0])) : STEPS[i].totals);
function interpTotals(){
  const a = totalsAt(cur - 1), b = totalsAt(cur);
  const o = {};
  for (const p of PLAYERS) o[p.id] = (a[p.id] || 0) + ((b[p.id] || 0) - (a[p.id] || 0)) * prog;
  return o;
}

const rowsEl = document.getElementById('rows');
const npStep = document.getElementById('np-step'), npLabel = document.getElementById('np-label'),
      npScore = document.getElementById('np-score'), npTeams = document.getElementById('np-teams'),
      npDate = document.getElementById('np-date'), npBanner = document.getElementById('nowplaying');
const elStep = document.getElementById('stepno');
const playBtn = document.getElementById('play'), scrub = document.getElementById('scrub'),
      speedBtn = document.getElementById('speed');
let shownStep = -1;  // drives the banner flash when the match changes

function renderHUD(){
  if (!NSTEP) return;
  const t = interpTotals();
  const order = PLAYERS.slice().sort((p,q)=> (t[q.id]-t[p.id]) || p.name.localeCompare(q.name));
  // rank change vs the previous settled step
  const prevRanks = (cur>0 ? STEPS[cur-1].ranks : STEPS[0].ranks);
  const prevPos = Object.fromEntries(prevRanks.map((id,i)=>[id,i]));
  rowsEl.innerHTML = order.map((p,i)=>{
    const d = (prevPos[p.id] ?? i) - i;
    const arr = d>0 ? ['up','▲'] : d<0 ? ['down','▼'] : ['same','—'];
    return `<div class="row${i===0?' lead':''}">
      <span class="pos">${i+1}</span>
      <span class="dot" style="color:${p.color}"></span>
      <span class="nm" title="${p.full||p.name}">${p.name}</span>
      <span class="pts" style="color:${p.color}">${Math.round(t[p.id])}</span>
      <span class="arr ${arr[0]}">${arr[1]}</span>
    </div>`;
  }).join('');
  const s = STEPS[cur];
  npStep.textContent = `матч ${cur+1}/${NSTEP}`;
  npLabel.textContent = s.label;
  npScore.textContent = s.score;
  npTeams.textContent = (s.home && s.away) ? `${s.home} — ${s.away}` : '';
  npDate.textContent = s.date;
  elStep.textContent = `${cur+1}/${NSTEP}`;
  if (cur !== shownStep){            // flash the banner each time a new match comes up
    shownStep = cur;
    npBanner.classList.remove('flash'); void npBanner.offsetWidth; npBanner.classList.add('flash');
  }
}

function goTo(i, snap){
  cur = Math.max(0, Math.min(NSTEP-1, i|0));
  prog = 1; scrub.value = String(cur); renderHUD();
}
function setPlaying(v){
  playing = v && NSTEP>1;
  playBtn.textContent = playing ? '❚❚' : '▶';
  if (playing && cur>=NSTEP-1 && prog>=1){ cur=0; prog=0; } // restart from the top
}
const boardEl = document.getElementById('board');
function setBoardCollapsed(v){
  boardEl.classList.toggle('collapsed', v);
  document.getElementById('boardChev').textContent = v ? '▸' : '▾';
}
document.getElementById('boardToggle').onclick = ()=> setBoardCollapsed(!boardEl.classList.contains('collapsed'));
// on phones the full table would cover the runners — start collapsed, tap to peek
if (matchMedia('(max-width:640px)').matches) setBoardCollapsed(true);
playBtn.onclick = ()=> setPlaying(!playing);
speedBtn.onclick = ()=>{ speedIdx=(speedIdx+1)%SPEEDS.length; speedBtn.textContent = SPEEDS[speedIdx]+'×'; };
scrub.oninput = ()=>{ setPlaying(false); const v=parseFloat(scrub.value); cur=Math.round(v); prog=1; renderHUD(); };

function showMsg(html){ const m=document.getElementById('msg'); m.querySelector('div').innerHTML=html; m.style.display='flex'; }

if (!NSTEP){
  showMsg('<b>Гонка почнеться після перших зіграних матчів.</b><br>Коли матчі завершаться, тут зʼявиться 3D-таблиця руху всіх учасників.');
  document.getElementById('ctl').style.display='none';
  document.getElementById('board').style.display='none';
} else {
  scrub.max = String(NSTEP-1);
  goTo(0);
}

// ---- 3D scene (three.js) ---------------------------------------------------
let tick = ()=>{}; // replaced on success; HUD clock still drives via rAF below
let lastT = null;
function frame(now){
  requestAnimationFrame(frame);
  if (lastT==null) lastT = now;
  const dt = Math.min(now - lastT, 60); lastT = now;
  if (playing && NSTEP){
    prog += dt / (STEP_MS / SPEEDS[speedIdx]);
    while (prog >= 1){
      if (cur >= NSTEP-1){ prog=1; setPlaying(false); break; }
      cur += 1; prog -= 1;
    }
    renderHUD();
  }
  tick(dt);
}
requestAnimationFrame(frame);

(async function init3D(){
  if (!NSTEP) return;
  let THREE, OrbitControls, EffectComposer, RenderPass, UnrealBloomPass;
  try {
    THREE = await import('three');
    ({ OrbitControls } = await import('three/addons/controls/OrbitControls.js'));
    ({ EffectComposer } = await import('three/addons/postprocessing/EffectComposer.js'));
    ({ RenderPass } = await import('three/addons/postprocessing/RenderPass.js'));
    ({ UnrealBloomPass } = await import('three/addons/postprocessing/UnrealBloomPass.js'));
  } catch (e){
    // No WebGL / offline: the 2D leaderboard + scrubber already work. Hint at canvas.
    document.getElementById('scene').style.background =
      'radial-gradient(80% 60% at 50% 30%, rgba(52,225,255,.10), transparent 70%)';
    return;
  }
  const canvas = document.getElementById('scene');
  const renderer = new THREE.WebGLRenderer({canvas, antialias:true, alpha:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, innerWidth/innerHeight, 0.1, 500);
  // side view from -Z: start on the left, finish on the right, runners run rightwards.
  // (fixed side, no auto-spin, so floor phase labels never read mirrored)
  const portrait = innerHeight > innerWidth;
  const CAM = portrait ? {dx:-6, y:30, z:40} : {dx:-12, y:18, z:50};
  camera.position.set(TRACK_LEN*0.5 + CAM.dx, CAM.y, CAM.z);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(TRACK_LEN*0.42, 1.2, 0);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.autoRotate = false;
  controls.minDistance = 18; controls.maxDistance = 140;

  scene.add(new THREE.AmbientLight(0x9fb6d8, 1.6)); // floodlit-evening fill so the grass reads green
  const key = new THREE.PointLight(0x66ccff, 0.6, 0, 2); key.position.set(20,40,30); scene.add(key);

  // stadium pitch (XZ plane: X = points/track, Z = lanes) — green turf instead of an abstract grid
  const FIELD_HALF = PLAYERS.length*LANE_GAP/2 + 3; // half-depth of the playing surface in Z
  const FIELD_X0 = -6, FIELD_X1 = TRACK_LEN + 6;
  const turf = new THREE.Mesh(
    new THREE.PlaneGeometry(FIELD_X1 - FIELD_X0, FIELD_HALF*2),
    new THREE.MeshBasicMaterial({color:0x0f7a37}));
  turf.rotation.x = -Math.PI/2; turf.position.set((FIELD_X0+FIELD_X1)/2, -0.01, 0); scene.add(turf);
  // mowing stripes along X — alternating shades read as a manicured pitch (no white line markings)
  function pitchStripe(x0, x1, shade){
    const m = new THREE.Mesh(new THREE.PlaneGeometry(x1-x0, FIELD_HALF*2),
      new THREE.MeshBasicMaterial({color:shade, transparent:true, opacity:0.18, depthWrite:false}));
    m.rotation.x = -Math.PI/2; m.position.set((x0+x1)/2, 0.0, 0); scene.add(m);
  }
  const STRIPES = 16, sw0 = (FIELD_X1-FIELD_X0)/STRIPES;
  for (let i=0;i<STRIPES;i++){ pitchStripe(FIELD_X0+i*sw0, FIELD_X0+(i+1)*sw0, i%2 ? 0x1c9a4a : 0x0a5f2a); }

  // raked seating tiers — boxes stepping up and outward. The camera is fixed on the +Z
  // touchline, so the far side (-Z) gets the tall main grandstand and the near side only
  // low boards, otherwise the near stand would wall off the runners.
  function stand(side, tiers, hScale){ // side = +1 / -1 along Z
    const baseZ = FIELD_HALF + 2.5;
    for (let i=0;i<tiers;i++){
      const h = (2 + i*1.6)*hScale;
      const t = new THREE.Mesh(
        new THREE.BoxGeometry(TRACK_LEN*1.15, h, 3),
        new THREE.MeshBasicMaterial({color: i%2 ? 0x1a2748 : 0x223255}));
      t.position.set(TRACK_LEN/2, h/2 + i*1.2*hScale, side*(baseZ + i*2.6));
      scene.add(t);
    }
  }
  stand(-1, 4, 1.0);  // main grandstand across the pitch (far side only — the near side is
                      // left open so the camera's view of the runners is never walled off)

  // floodlight pylons at the four corners — glowing heads + point lights for a night-match feel
  function pylon(x, z){
    const mast = new THREE.Mesh(new THREE.BoxGeometry(0.5, 26, 0.5),
      new THREE.MeshBasicMaterial({color:0x2a3a6a}));
    mast.position.set(x, 13, z); scene.add(mast);
    const head = new THREE.Mesh(new THREE.BoxGeometry(2.8, 1.0, 0.5),
      new THREE.MeshBasicMaterial({color:0xcfe8ff})); // bright -> caught by bloom
    head.position.set(x, 26.2, z); scene.add(head);
    const lamp = new THREE.PointLight(0xfff2d8, 0.45, 140, 2); lamp.position.set(x, 24, z*0.7); scene.add(lamp);
  }
  const PZ = FIELD_HALF + 9;
  pylon(2, PZ); pylon(2, -PZ); pylon(TRACK_LEN-2, PZ); pylon(TRACK_LEN-2, -PZ);

  // small football goals at the start and finish lines — just the white frame (posts + crossbar),
  // centred on the track. The leader curls the ball into the finish frame at the end of the race.
  const GOAL_HALF = 4.0, GOAL_H = 3.4, POST_R = 0.13, GOAL_OFF = 3.0; // sit just beyond the group zones
  function goal(gx){
    const white = new THREE.MeshBasicMaterial({color:0xffffff}); // bright -> bloom glow
    function post(z){ const m = new THREE.Mesh(new THREE.CylinderGeometry(POST_R, POST_R, GOAL_H, 10), white); m.position.set(gx, GOAL_H/2, z); scene.add(m); }
    post(GOAL_HALF); post(-GOAL_HALF);
    const cross = new THREE.Mesh(new THREE.CylinderGeometry(POST_R, POST_R, GOAL_HALF*2, 10), white);
    cross.rotation.x = Math.PI/2; cross.position.set(gx, GOAL_H, 0); scene.add(cross);
  }
  goal(-GOAL_OFF); goal(TRACK_LEN + GOAL_OFF);

  function labelSprite(text, color){
    const c = document.createElement('canvas'); c.width=256; c.height=64;
    const x = c.getContext('2d');
    x.font='600 34px "Space Grotesk", sans-serif'; x.textAlign='center'; x.textBaseline='middle';
    x.lineWidth=5; x.strokeStyle='rgba(5,8,18,0.92)'; x.strokeText(text,128,34);
    x.fillStyle=color; x.fillText(text,128,34);
    const tex = new THREE.CanvasTexture(c); tex.anisotropy=4;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:tex, transparent:true, depthWrite:false}));
    sp.scale.set(5.5,1.375,1); return sp; // keep 4:1 aspect; smaller so names don't cover the ball
  }

  // phase caption painted flat on the floor (runners run over it), reads along the track
  function floorText(text, color, maxW){
    const font='600 34px "Space Grotesk", sans-serif';
    const meas=document.createElement('canvas').getContext('2d'); meas.font=font;
    const tw=Math.ceil(meas.measureText(text).width)+44;
    const c=document.createElement('canvas'); c.width=tw; c.height=64;
    const x=c.getContext('2d');
    x.font=font; x.textAlign='center'; x.textBaseline='middle';
    x.lineWidth=5; x.strokeStyle='rgba(5,8,18,0.92)'; x.strokeText(text, tw/2, 34);
    x.fillStyle=color; x.fillText(text, tw/2, 34);
    const tex=new THREE.CanvasTexture(c); tex.anisotropy=4;
    let Wm=tw/22; if(maxW) Wm=Math.min(Wm, maxW);
    const m=new THREE.Mesh(new THREE.PlaneGeometry(Wm, Wm*64/tw),
      new THREE.MeshBasicMaterial({map:tex, transparent:true, opacity:0.5, depthWrite:false}));
    m.rotation.x=-Math.PI/2; // lay flat on the ground (XZ plane)
    return m;
  }

  // coloured track zones — one per phase (Група 1/2/3 …), drawn along the runners' path
  const LANE_SPAN = PLAYERS.length*LANE_GAP + 2;
  (DATA.bands||[]).forEach(b=>{
    const x0=xOf(b.from), x1=xOf(b.to), w=Math.max(x1-x0, 0.2), col=new THREE.Color(b.color);
    const zone=new THREE.Mesh(new THREE.PlaneGeometry(w, LANE_SPAN),
      new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:0.14, depthWrite:false}));
    zone.rotation.x=-Math.PI/2; zone.position.set((x0+x1)/2, 0.02, 0); scene.add(zone);
    const line=new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.05, LANE_SPAN),
      new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:0.55}));
    line.position.set(x1, 0.06, 0); scene.add(line);
    const lbl=floorText(b.label, b.color, w*0.92);
    lbl.position.set((x0+x1)/2, 0.08, LANE_SPAN/2 - 1.6); scene.add(lbl);
  });

  // a neon stick-runner built from primitives — faces +X (down the track);
  // limbs hang from hip/shoulder pivots and swing around Z for the run cycle.
  function makeRunner(color){
    const mat = new THREE.MeshBasicMaterial({color:new THREE.Color(color)});
    const g = new THREE.Group();
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.26, 0.7, 4, 8), mat);
    torso.position.y = 1.25; g.add(torso);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.30, 16, 16), mat);
    head.position.y = 1.95; g.add(head);
    function limb(py, len, r, z){
      const pivot = new THREE.Group(); pivot.position.set(0, py, z);
      const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, len, 4, 6), mat);
      m.position.y = -(len/2 + r); pivot.add(m); g.add(pivot); return pivot;
    }
    const legL = limb(0.95, 0.7, 0.12,  0.15), legR = limb(0.95, 0.7, 0.12, -0.15);
    const armL = limb(1.6,  0.55, 0.09,  0.30), armR = limb(1.6,  0.55, 0.09, -0.30);
    g.rotation.z = -0.08; // slight forward lean into the run
    g.scale.setScalar(1.3);
    return {g, legL, legR, armL, armR};
  }

  const TRAIL = 90;
  const runners = PLAYERS.map((p,i)=>{
    const col = new THREE.Color(p.color);
    const rn = makeRunner(p.color);
    const label = labelSprite(p.name, p.color); label.position.set(0,2.9,0); rn.g.add(label);
    scene.add(rn.g);
    const positions = new Float32Array(TRAIL*3);
    const tgeo = new THREE.BufferGeometry();
    tgeo.setAttribute('position', new THREE.BufferAttribute(positions,3));
    const trail = new THREE.Line(tgeo, new THREE.LineBasicMaterial({color:col, transparent:true, opacity:0.5}));
    trail.frustumCulled = false; scene.add(trail);
    return {p, rn, trail, positions, filled:0, phase:i*0.7};
  });

  // football dribbled in front of whoever currently leads the race — a white sphere with
  // black pentagon patches at the 12 icosahedron vertices (the classic Telstar look).
  const BALL_R = 0.45, BALL_AHEAD = 1.4;
  function makeBall(){
    const g = new THREE.Group();
    g.add(new THREE.Mesh(new THREE.SphereGeometry(BALL_R, 24, 24),
      new THREE.MeshBasicMaterial({color:0xffffff})));
    const PHI = 1.618033988749895;
    const verts = [[0,1,PHI],[0,1,-PHI],[0,-1,PHI],[0,-1,-PHI],
      [1,PHI,0],[1,-PHI,0],[-1,PHI,0],[-1,-PHI,0],
      [PHI,0,1],[PHI,0,-1],[-PHI,0,1],[-PHI,0,-1]];
    const black = new THREE.MeshBasicMaterial({color:0x10131a, side:THREE.DoubleSide});
    for (const v of verts){
      const dir = new THREE.Vector3(v[0],v[1],v[2]).normalize();
      const patch = new THREE.Mesh(new THREE.CircleGeometry(BALL_R*0.46, 5), black);
      patch.position.copy(dir.clone().multiplyScalar(BALL_R*0.999));
      patch.lookAt(dir.clone().multiplyScalar(BALL_R*4)); // lie tangent, facing outward
      g.add(patch);
    }
    return g;
  }
  const ball = makeBall(); ball.visible = false; scene.add(ball);
  let ballX = null, ballZ = 0;      // ball's own glided position (lags the leader -> reads as a pass)
  let lastBX = 0, lastBZ = 0;       // previous frame position, for roll
  let shotProg = 0, shotFromX = 0, shotFromZ = 0; // finish-line shot into the net (0..1)

  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.55, 0.45, 0.2);
  composer.addPass(bloom);

  let runPhase = 0;
  tick = function(dt){
    runPhase += (dt||16) * (playing ? 0.02*SPEEDS[speedIdx] : 0.007);
    const t = interpTotals();
    let sumX = 0;
    for (const r of runners){
      const id = r.p.id;
      const x = xOf(t[id]||0); sumX += x;
      const z = laneZ(laneIndex[id]); // fixed lane — overtakes show as forward distance only
      const ph = runPhase + r.phase;
      const sw = Math.sin(ph);
      const bob = Math.abs(sw) * 0.10;
      r.rn.g.position.set(x, bob, z);
      r.rn.legL.rotation.z =  sw*0.7; r.rn.legR.rotation.z = -sw*0.7;
      r.rn.armL.rotation.z = -sw*0.5; r.rn.armR.rotation.z =  sw*0.5;
      // push torso point into trail ring buffer
      const arr = r.positions, yy = 1.05 + bob;
      if (r.filled < TRAIL) { const k=r.filled*3; arr[k]=x; arr[k+1]=yy; arr[k+2]=z; r.filled++; }
      else { arr.copyWithin(0, 3); const k=(TRAIL-1)*3; arr[k]=x; arr[k+1]=yy; arr[k+2]=z; }
      r.trail.geometry.setDrawRange(0, r.filled);
      r.trail.geometry.attributes.position.needsUpdate = true;
    }
    // football glides to a spot just ahead of the current leader; on a lead change the target
    // jumps to the new lane and the ball rolls across to it — reads as a pass between players.
    // Once the race settles on its final step, the leader buries the ball in the finish net.
    if (runners.length){
      let leadId = null, leadX = -Infinity;
      for (const r of runners){ const x = xOf(t[r.p.id]||0); if (x > leadX){ leadX = x; leadId = r.p.id; } }
      const tx = leadX + BALL_AHEAD, tz = laneZ(laneIndex[leadId]);
      if (ballX === null){ ballX = tx; ballZ = tz; lastBX = tx; lastBZ = tz; } // first frame
      const atEnd = (cur >= NSTEP-1) && (prog >= 1);
      if (atEnd){ if (shotProg === 0){ shotFromX = ballX; shotFromZ = ballZ; } shotProg = Math.min(1, shotProg + (dt||16)/650); }
      else shotProg = Math.max(0, shotProg - (dt||16)/250);

      let bx, by, bz;
      if (shotProg <= 0){
        ballX += (tx - ballX) * 0.08; ballZ += (tz - ballZ) * 0.08; // dribble toward the leader
        bx = ballX; bz = ballZ; by = BALL_R + Math.abs(Math.sin(runPhase*1.4)) * 0.10;
      } else {
        const e = 1 - Math.pow(1 - shotProg, 3); // ease-out
        const netX = TRACK_LEN + GOAL_OFF - 0.3, netY = 1.2, netZ = 0; // rest on the goal line, not past it
        bx = shotFromX + (netX - shotFromX) * e;
        bz = shotFromZ + (netZ - shotFromZ) * e;
        by = BALL_R + (netY - BALL_R) * e + Math.sin(Math.PI * e) * 1.5; // arc over the line
        ballX = bx; ballZ = bz;
      }
      ball.visible = true;
      ball.position.set(bx, by, bz);
      const dx = bx - lastBX, dz = bz - lastBZ, dist = Math.hypot(dx, dz);
      if (dist > 1e-4) ball.rotateOnWorldAxis(new THREE.Vector3(dz,0,-dx).normalize(), dist/BALL_R); // roll
      lastBX = bx; lastBZ = bz;
    }
    // keep the camera framing the moving pack
    const meanX = runners.length ? sumX/runners.length : TRACK_LEN/2;
    controls.target.x += (meanX - controls.target.x)*0.05;
    controls.target.y += (1.2 - controls.target.y)*0.05;
    controls.target.z += (0 - controls.target.z)*0.05;
    camera.position.x += (controls.target.x + CAM.dx - camera.position.x)*0.05; // pan with the pack
    controls.update();
    composer.render();
  };

  function resize(){
    camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
  }
  addEventListener('resize', resize); resize();
})();
</script>
</body>
</html>
"""


def render_standings(timeline, generated_at):
    return (STANDINGS_TEMPLATE
            .replace("__DATA__", json.dumps(timeline, ensure_ascii=False))
            .replace("__GENERATED__", esc(generated_at)))


def group_by_phase(rendered, phases):
    """rendered: [(match, n, fname)] newest-first. Returns [(label_or_None, items)],
    phases ordered by their latest match (most recent phase first). Falls back to one
    unheaded group when phase metadata is missing (older dumps / synthetic data)."""
    phase_meta = {ph["id"]: ph for ph in (phases or []) if ph.get("id")}
    if not phase_meta:
        return [(None, rendered)]
    by_pid = {}
    for m, n, fn in rendered:
        by_pid.setdefault(m.get("phaseId"), []).append((m, n, fn))
    order = sorted(by_pid, key=lambda pid: max(
        (mm.get("timeStamp", 0) for mm, _, _ in by_pid[pid]), default=0), reverse=True)
    return [(phase_label(phase_meta.get(pid)), by_pid[pid]) for pid in order]


def build_site(participants, matches, preds, out_dir, show_all, only_match, phases=None):
    os.makedirs(out_dir, exist_ok=True)
    selected = []
    for mid, m in matches.items():
        if only_match:
            want = {c.upper() for c in only_match.replace("–", "-").split("-")}
            got = {code(m, "home"), code(m, "away")}
            if not want.issubset(got):
                continue
        elif not show_all and not has_started(m):
            continue
        selected.append((mid, m))
    # newest first
    selected.sort(key=lambda kv: kv[1].get("timeStamp", 0), reverse=True)

    rendered = []
    for mid, m in selected:
        pfm = preds.get(mid, {})
        fname = f"match-{mid}.html"
        with open(os.path.join(out_dir, fname), "w", encoding="utf-8") as f:
            f.write(render_match(m, participants, pfm))
        rendered.append((m, len(pfm), fname))

    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_index(group_by_phase(rendered, phases), generated_at))

    # standings race page — cumulative match points over every finished match
    timeline = build_timeline(participants, matches, preds, phases)
    with open(os.path.join(out_dir, "standings.html"), "w", encoding="utf-8") as f:
        f.write(render_standings(timeline, generated_at))
    return rendered


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--token", help="Bearer token (else POOL_API_TOKEN env / .env)")
    ap.add_argument("--pool-id", default=None, help=f"pool id (default {DEFAULT_POOL_ID})")
    ap.add_argument("--out", default=DEFAULT_OUT, help="output dir (default <footbal>/pool)")
    ap.add_argument("--all", action="store_true",
                    help="include matches that have not started yet")
    ap.add_argument("--match", help="render only one match, e.g. PAN-ENG")
    ap.add_argument("--dump", help="save the assembled data as JSON to this file")
    ap.add_argument("--input", help="render from a --dump file instead of calling the API")
    args = ap.parse_args()

    load_dotenv()
    pool_id = args.pool_id or os.environ.get("POOL_ID") or DEFAULT_POOL_ID

    if args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
        participants = data["participants"]
        matches = data["matches"]
        preds = {mid: {u: v for u, v in users.items()}
                 for mid, users in data["preds"].items()}
        phases = data.get("phases", [])
    else:
        token = args.token or os.environ.get("POOL_API_TOKEN")
        if not token:
            sys.exit("error: no token. Pass --token <Bearer> or set POOL_API_TOKEN in "
                     ".env. Get it from the browser DevTools -> Network -> any "
                     "footballpool-api request -> Authorization header.")
        participants, matches, preds, phases = collect(token, pool_id)
        if args.dump:
            with open(args.dump, "w", encoding="utf-8") as f:
                json.dump({"participants": participants, "matches": matches,
                           "preds": preds, "phases": phases}, f,
                          ensure_ascii=False, indent=2)
            print(f"dumped raw data: {args.dump}")

    rendered = build_site(participants, matches, preds, args.out, args.all, args.match,
                          phases)
    print(f"participants: {len(participants)} · matches rendered: {len(rendered)}")
    print(f"site: {os.path.join(args.out, 'index.html')}")
    if not rendered:
        print("note: no started matches yet — others' predictions appear only after "
              "kickoff. Use --all to include upcoming matches anyway.")


if __name__ == "__main__":
    main()
