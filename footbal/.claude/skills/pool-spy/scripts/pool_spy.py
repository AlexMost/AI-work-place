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
from datetime import datetime, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
    PRAGUE = ZoneInfo("Europe/Prague")
except Exception:
    # tzdata unavailable: fall back to CEST (UTC+2), correct for the summer WC window
    PRAGUE = timezone(timedelta(hours=2))

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
    # timeStamp is the authoritative UTC epoch (same field has_started/sorting use);
    # startDate is naive *Prague-local* — parsing it as UTC double-shifts by +2h.
    ts = m.get("timeStamp")
    if ts:
        return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(PRAGUE).strftime("%d.%m %H:%M")
    sd = m.get("startDate")
    if not sd:
        return ""
    try:
        dt = datetime.fromisoformat(sd.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=PRAGUE)
        return dt.astimezone(PRAGUE).strftime("%d.%m %H:%M")
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


# --- country flags (flagcdn PNGs) ------------------------------------------

# Full team name (as the API returns it) -> ISO 3166-1 alpha-2 (lowercase), the
# code flagcdn expects. England/Scotland use flagcdn's GB-subdivision flags.
# Keys are matched case-insensitively with "&"<->"and" normalised (see flag_iso).
TEAM_ISO = {
    "algeria": "dz", "argentina": "ar", "australia": "au", "austria": "at",
    "belgium": "be", "bosnia & herzegovina": "ba", "brazil": "br", "canada": "ca",
    "cape verde islands": "cv", "colombia": "co", "congo dr": "cd", "croatia": "hr",
    "curacao": "cw", "czech republic": "cz", "ecuador": "ec", "egypt": "eg",
    "england": "gb-eng", "france": "fr", "germany": "de", "ghana": "gh",
    "haiti": "ht", "iran": "ir", "iraq": "iq", "ivory coast": "ci", "japan": "jp",
    "jordan": "jo", "mexico": "mx", "morocco": "ma", "netherlands": "nl",
    "new zealand": "nz", "norway": "no", "panama": "pa", "paraguay": "py",
    "portugal": "pt", "qatar": "qa", "saudi arabia": "sa", "scotland": "gb-sct",
    "senegal": "sn", "south africa": "za", "south korea": "kr", "spain": "es",
    "sweden": "se", "switzerland": "ch", "tunisia": "tn", "turkiye": "tr",
    "usa": "us", "uruguay": "uy", "uzbekistan": "uz",
    # alias spellings the API/sources sometimes use
    "bosnia and herzegovina": "ba", "bosnia-herzegovina": "ba", "turkey": "tr",
    "united states": "us", "korea republic": "kr", "republic of korea": "kr",
    "cape verde": "cv", "dr congo": "cd", "congo dr.": "cd", "cote d'ivoire": "ci",
    "wales": "gb-wls", "northern ireland": "gb-nir", "czechia": "cz",
}

_FLAG_WARNED = set()


def _flag_key(name):
    # Lower-case and drop the two accents that appear in the field (Türkiye, Curaçao).
    return (name or "").strip().lower().replace("ü", "u").replace("ç", "c")


def flag_iso(name):
    if not name:
        return None
    k = _flag_key(name)
    iso = TEAM_ISO.get(k) or TEAM_ISO.get(k.replace(" and ", " & "))
    if iso is None and k not in _FLAG_WARNED:
        _FLAG_WARNED.add(k)
        print(f"[pool-spy] no flag mapping for team {name!r}", file=sys.stderr)
    return iso


def flag_img(name, cls=""):
    """flagcdn <img> for a team, or '' when the name isn't mapped (graceful)."""
    iso = flag_iso(name)
    if not iso:
        return ""
    return (f'<img src="https://flagcdn.com/w40/{iso}.png" '
            f'srcset="https://flagcdn.com/w80/{iso}.png 2x" '
            f'width="40" height="30" loading="lazy" alt="" '
            f'class="{cls}">')


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


# Ручні коригування рейтингу пулу: учасник приєднався пізно й отримав стартовий
# бонус від організаторів. У скрапнутих per-match points цього немає, тож додаємо
# тут — впливає на гонку в standings.html (таблиця + 3D-позиція бігуна).
BONUS_ADJUSTMENTS = {"ed536a15-cf36-4169-ad18-2bb832473694": 20}  # Andrew Shtanko +20


def build_timeline(participants, matches, preds, phases=None):
    """Cumulative match-points standings after each finished match, chronologically.

    Returns {"players":[...], "steps":[...], "maxTotal":int, "bands":[...]} where bands
    are coloured stretches of the track, one per phase, spanning the pool's average
    cumulative points from the phase's start to its end.
    Only players who share predictions are included (matches the rest of the site).
    NOTE: per-match `points` excludes bonus-question points, so totals here are the
    match-points race, not necessarily the pool's official standing. Totals may also
    include a manual `BONUS_ADJUSTMENTS` seed (e.g. a late-joiner's start bonus).
    """
    pred_uids = set()
    for users in preds.values():
        pred_uids.update(users.keys())
    players = [p for p in participants
               if p.get("allowPredictionSharing", True) and p["id"] in pred_uids]
    players.sort(key=lambda x: x.get("rank", 999))

    finished = [(mid, m) for mid, m in matches.items() if is_finished(m)]
    finished.sort(key=lambda kv: kv[1].get("timeStamp", 0))

    cumulative = {p["id"]: BONUS_ADJUSTMENTS.get(p["id"], 0) for p in players}
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
            "homeIso": flag_iso(m.get("homeTeamName", "")) or "",
            "awayIso": flag_iso(m.get("awayTeamName", "")) or "",
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
    date_part, _, time_part = fmt_date(m).partition(" ")
    return f"""
  <a href="{esc(fname)}" class="block bg-white rounded-xl shadow-sm hover:shadow-md
     ring-1 ring-slate-200 transition px-4 py-3 flex items-center gap-3">
    <div class="w-11 shrink-0 leading-tight">
      <div class="text-xs text-slate-400">{esc(date_part)}</div>
      <div class="text-sm font-semibold text-slate-600 tabular-nums">{esc(time_part)}</div>
    </div>
    <div class="flex-1 min-w-0">
      <div class="hidden sm:block">
        <div class="font-semibold tracking-wide whitespace-nowrap">{esc(match_label(m))}</div>
        <div class="text-sm text-slate-500 truncate">{flag_img(m.get('homeTeamName',''), 'inline-block w-5 h-auto rounded-sm align-[-2px] mr-1')}{esc(m.get('homeTeamName',''))} — {flag_img(m.get('awayTeamName',''), 'inline-block w-5 h-auto rounded-sm align-[-2px] mr-1')}{esc(m.get('awayTeamName',''))}</div>
      </div>
      <div class="sm:hidden inline-grid grid-cols-[1fr_auto_1fr] gap-x-2 text-center items-center">
        <div class="font-semibold tracking-wide">{esc(code(m, 'home'))}</div>
        <div class="font-semibold tracking-wide text-slate-400">–</div>
        <div class="font-semibold tracking-wide">{esc(code(m, 'away'))}</div>
        <div class="mt-0.5">{flag_img(m.get('homeTeamName',''), 'inline-block w-5 h-auto rounded-sm')}</div>
        <div class="text-slate-400">–</div>
        <div class="mt-0.5">{flag_img(m.get('awayTeamName',''), 'inline-block w-5 h-auto rounded-sm')}</div>
      </div>
    </div>
    <div class="shrink-0 text-right leading-tight">
      <div class="text-lg font-bold tabular-nums">{esc(score_txt)}</div>
      <div class="flex items-center justify-end gap-1.5 mt-0.5">
        <span class="text-[10px] px-1.5 py-0.5 rounded-full whitespace-nowrap {label_cls}">{esc(label)}</span>
        <span class="text-[11px] text-slate-400 whitespace-nowrap">{n_pred} прог.</span>
      </div>
    </div>
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
  <p class="text-xs text-slate-400 mt-8">оновлено {esc(generated_at)} · час за Прагою</p>
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
    <h1 class="text-2xl font-bold mt-2 flex items-center justify-center gap-2 flex-wrap">
       {flag_img(m.get('homeTeamName',''), 'inline-block w-7 h-auto rounded-sm shadow-sm')}{esc(m.get('homeTeamName',''))}
       <span class="text-slate-400">—</span>
       {flag_img(m.get('awayTeamName',''), 'inline-block w-7 h-auto rounded-sm shadow-sm')}{esc(m.get('awayTeamName',''))}</h1>
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
  .np-flag{display:inline-block; width:16px; height:auto; border-radius:2px; vertical-align:-2px; margin-right:4px; box-shadow:0 0 0 1px rgba(255,255,255,.15)}
  .np-date{font-size:12px; color:var(--text-dim)}
  /* leaderboard */
  #board{
    left:18px; top:104px; width:min(40vw,300px);
    background:var(--glass); border:1px solid var(--glass-border);
    border-radius:14px; padding:10px 12px; backdrop-filter:blur(8px);
  }
  #board h2{margin:0 0 8px; font-size:11px; letter-spacing:.14em; text-transform:uppercase; color:var(--text-dim); font-weight:600;
            display:flex; align-items:center; justify-content:space-between; gap:8px; cursor:pointer; user-select:none;
            pointer-events:auto}
  #board h2 .chev{font-size:10px; opacity:.8}
  #board.collapsed{padding-bottom:10px; width:auto; max-height:none; overflow:visible}
  #board.collapsed #rows{display:none}
  #board.collapsed h2{margin-bottom:0}
  .row{display:flex; align-items:center; gap:8px; padding:4px 2px; font-size:14px}
  .row .pos{width:18px; text-align:right; color:var(--text-dim); font-variant-numeric:tabular-nums}
  .row .dot{width:10px; height:10px; border-radius:50%; flex:0 0 auto; background:currentColor; box-shadow:0 0 8px currentColor}
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
    <div class="sub">кумулятивні бали за матчі · оновлено __GENERATED__ · час за Прагою</div>
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
// random lane layout, shuffled once per page load, fixed for the whole run
const _laneOrder = PLAYERS.map((_, i) => i);
for (let i = _laneOrder.length - 1; i > 0; i--) {
  const j = Math.floor(Math.random() * (i + 1));
  [_laneOrder[i], _laneOrder[j]] = [_laneOrder[j], _laneOrder[i]];
}
const laneIndex = Object.fromEntries(PLAYERS.map((p, i) => [p.id, _laneOrder[i]])); // fixed lane per player
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
  if (s.home && s.away){
    const fl = (iso) => iso ? `<img class="np-flag" src="https://flagcdn.com/w40/${iso}.png" srcset="https://flagcdn.com/w80/${iso}.png 2x" alt="" loading="lazy">` : '';
    npTeams.innerHTML = `${fl(s.homeIso)}${s.home} — ${fl(s.awayIso)}${s.away}`;
  } else {
    npTeams.textContent = '';
  }
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
  let THREE, OrbitControls, EffectComposer, RenderPass, UnrealBloomPass, OutputPass, BGU;
  try {
    THREE = await import('three');
    ({ OrbitControls } = await import('three/addons/controls/OrbitControls.js'));
    ({ EffectComposer } = await import('three/addons/postprocessing/EffectComposer.js'));
    ({ RenderPass } = await import('three/addons/postprocessing/RenderPass.js'));
    ({ UnrealBloomPass } = await import('three/addons/postprocessing/UnrealBloomPass.js'));
    ({ OutputPass } = await import('three/addons/postprocessing/OutputPass.js'));
    BGU = await import('three/addons/utils/BufferGeometryUtils.js');
  } catch (e){
    // No WebGL / offline: the 2D leaderboard + scrubber already work. Hint at canvas.
    document.getElementById('scene').style.background =
      'radial-gradient(80% 60% at 50% 30%, rgba(52,225,255,.10), transparent 70%)';
    return;
  }
  const isMobile = matchMedia('(pointer:coarse)').matches;
  const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let dprCap = isMobile ? 1.5 : 2;

  const canvas = document.getElementById('scene');
  const renderer = new THREE.WebGLRenderer({canvas, antialias:true});
  renderer.setPixelRatio(Math.min(devicePixelRatio, dprCap));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  let shadowsOn = !isMobile;
  if (shadowsOn){ renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; }

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070b18);
  scene.fog = new THREE.FogExp2(0x070b18, 0.0055);

  const camera = new THREE.PerspectiveCamera(55, innerWidth/innerHeight, 0.1, 700);
  // side view from +Z: start on the left, finish on the right, runners run rightwards.
  // (fixed side, no auto-spin, so floor phase labels never read mirrored)
  const portrait = innerHeight > innerWidth;
  const CAM = portrait ? {dx:-6, y:30, z:40} : {dx:-12, y:18, z:50};
  camera.position.set(TRACK_LEN*0.5 + CAM.dx, CAM.y, CAM.z);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(TRACK_LEN*0.42, 1.2, 0);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  controls.autoRotate = false;
  controls.minDistance = 18; controls.maxDistance = 140;
  // while the user is actively dragging (rotate/zoom/pan, incl. touch) we freeze the auto-follow
  // below so it never fights the gesture — that fight is what made the view snap/zoom on mobile.
  let userInteracting = false;
  controls.addEventListener('start', () => { userInteracting = true; });
  controls.addEventListener('end',   () => { userInteracting = false; });

  // ---- lighting rig: floodlit night match -----------------------------------
  scene.add(new THREE.AmbientLight(0x243252, 0.7));
  scene.add(new THREE.HemisphereLight(0x2a3a66, 0x0d3d20, 0.8));
  let sun = null;
  if (shadowsOn){
    sun = new THREE.DirectionalLight(0xbcd6ff, 1.7);
    sun.position.set(TRACK_LEN*0.5 + 14, 38, 26);
    sun.target.position.set(TRACK_LEN*0.5, 0, 0);
    sun.castShadow = true;
    sun.shadow.mapSize.set(1024, 1024);
    const sc = sun.shadow.camera;
    sc.near = 5; sc.far = 130; sc.left = -46; sc.right = 46; sc.top = 34; sc.bottom = -30;
    sun.shadow.bias = -0.0006;
    scene.add(sun, sun.target);
  }

  const FIELD_HALF = PLAYERS.length*LANE_GAP/2 + 3; // half-depth of the playing surface in Z
  const FIELD_X0 = -6, FIELD_X1 = TRACK_LEN + 6;
  const GOAL_HALF = 4.0, GOAL_H = 3.4, POST_R = 0.13, GOAL_OFF = 6.0;

  // ---- turf with baked mowing stripes (one texture, one draw call) ----------
  function turfTexture(){
    const W = 1024, H = 256;
    const c = document.createElement('canvas'); c.width = W; c.height = H;
    const x = c.getContext('2d');
    x.fillStyle = '#0c6a30'; x.fillRect(0, 0, W, H);
    const STR = 16, sw = W/STR;
    for (let i = 0; i < STR; i++){
      x.fillStyle = i%2 ? 'rgba(46,178,92,.30)' : 'rgba(6,66,28,.34)';
      x.fillRect(i*sw, 0, sw, H);
    }
    // soft dark vignette toward the touchlines so the pitch reads lit from above
    const gr = x.createLinearGradient(0, 0, 0, H);
    gr.addColorStop(0, 'rgba(4,10,8,.42)'); gr.addColorStop(.28, 'rgba(4,10,8,0)');
    gr.addColorStop(.72, 'rgba(4,10,8,0)'); gr.addColorStop(1, 'rgba(4,10,8,.42)');
    x.fillStyle = gr; x.fillRect(0, 0, W, H);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    return tex;
  }
  const turf = new THREE.Mesh(
    new THREE.PlaneGeometry(FIELD_X1 - FIELD_X0, FIELD_HALF*2),
    new THREE.MeshStandardMaterial({map: turfTexture(), roughness: .82, metalness: 0}));
  turf.rotation.x = -Math.PI/2; turf.position.set((FIELD_X0+FIELD_X1)/2, -0.01, 0);
  turf.receiveShadow = shadowsOn; scene.add(turf);
  // apron: dark ground plane far beyond the pitch so the bowl never floats on the void
  const apron = new THREE.Mesh(new THREE.PlaneGeometry(560, 560),
    new THREE.MeshLambertMaterial({color: 0x0a1022}));
  apron.rotation.x = -Math.PI/2; apron.position.set(TRACK_LEN/2, -0.06, 0); scene.add(apron);

  // ---- stadium bowl: merged tiers + seat positions for the crowd ------------
  const tierGeosA = [], tierGeosB = [], seatPts = [];
  const seatStep = isMobile ? 1.7 : 0.85;
  const _m = new THREE.Matrix4();
  function tierBox(w, h, d, x, y, z, rotY, alt){
    const g = new THREE.BoxGeometry(w, h, d);
    _m.makeRotationY(rotY); g.applyMatrix4(_m);
    _m.makeTranslation(x, y, z); g.applyMatrix4(_m);
    (alt ? tierGeosB : tierGeosA).push(g);
  }
  function seatsOnTier(w, x, yTop, z, rotY){
    for (let row = 0; row < 2; row++){
      const lz = -0.75 + row*1.05;
      for (let lx = -w/2 + 1; lx <= w/2 - 1; lx += seatStep){
        const cos = Math.cos(rotY), sin = Math.sin(rotY);
        seatPts.push(x + lx*cos + lz*sin, yTop, z - lx*sin + lz*cos);
      }
    }
  }
  function bowlSide(rotY, cx, cz, tiers, hScale, len){
    for (let i = 0; i < tiers; i++){
      const h = (2 + i*1.6)*hScale, off = i*2.6;
      const wx = cx + off*Math.sin(rotY), wz = cz + off*Math.cos(rotY);
      const y = h/2 + i*1.2*hScale;
      tierBox(len, h, 3, wx, y, wz, rotY, i%2 === 1);
      seatsOnTier(len, wx, y + h/2 + 0.30, wz, rotY);
    }
  }
  const BOWL_Z = FIELD_HALF + 2.5;
  bowlSide(Math.PI,    TRACK_LEN/2, -BOWL_Z, 5, 1.05, TRACK_LEN*1.30); // main grandstand (far)
  bowlSide(0,          TRACK_LEN/2,  BOWL_Z, 2, 0.55, TRACK_LEN*1.15); // low near stand
  bowlSide(Math.PI/2,  TRACK_LEN + GOAL_OFF + 17, 0, 3, 0.8, FIELD_HALF*2 + 14); // finish end
  bowlSide(-Math.PI/2, -(GOAL_OFF + 17),          0, 3, 0.8, FIELD_HALF*2 + 14); // start end
  const merge = BGU.mergeGeometries || BGU.mergeBufferGeometries;
  const bowlA = new THREE.Mesh(merge(tierGeosA), new THREE.MeshLambertMaterial({color: 0x223255}));
  const bowlB = new THREE.Mesh(merge(tierGeosB), new THREE.MeshLambertMaterial({color: 0x1a2748}));
  scene.add(bowlA, bowlB);
  // roof slab + glowing edge strip over the main grandstand — night-match signature
  const roofY = 15.6, roofZ = -(BOWL_Z + 4*2.6*0.5 + 3.5);
  const roof = new THREE.Mesh(new THREE.BoxGeometry(TRACK_LEN*1.32, 0.4, 12),
    new THREE.MeshLambertMaterial({color: 0x141d38}));
  roof.position.set(TRACK_LEN/2, roofY, roofZ); scene.add(roof);
  const roofStrip = new THREE.Mesh(new THREE.BoxGeometry(TRACK_LEN*1.32, 0.22, 0.22),
    new THREE.MeshStandardMaterial({color: 0x101a33, emissive: 0x9fc4ff, emissiveIntensity: 2.2}));
  roofStrip.position.set(TRACK_LEN/2, roofY - 0.28, roofZ + 6.05); scene.add(roofStrip);

  // ---- instanced crowd: shader-animated, zero per-frame CPU -----------------
  const crowdN = Math.floor(seatPts.length/3);
  const crowdUni = { uTime: {value: 0}, uJump: {value: 0} };
  let crowd = null;
  if (crowdN > 0){
    const cg = new THREE.IcosahedronGeometry(0.42, 0);
    cg.scale(1, 1.55, 1); cg.translate(0, 0.55, 0);
    const phases = new Float32Array(crowdN);
    for (let i = 0; i < crowdN; i++) phases[i] = Math.random();
    cg.setAttribute('aPhase', new THREE.InstancedBufferAttribute(phases, 1));
    const cm = new THREE.MeshLambertMaterial({flatShading: true});
    cm.onBeforeCompile = (sh)=>{
      sh.uniforms.uTime = crowdUni.uTime;
      sh.uniforms.uJump = crowdUni.uJump;
      sh.vertexShader = sh.vertexShader
        .replace('#include <common>',
          '#include <common>\nattribute float aPhase;\nuniform float uTime;\nuniform float uJump;')
        .replace('#include <begin_vertex>',
          ['#include <begin_vertex>',
           'float _sway = 0.05*sin(uTime*2.2 + aPhase*17.0);',
           'float _jump = uJump*(0.55*abs(sin(uTime*6.0 + aPhase*6.2831))',
           '  + 0.12*sin(uTime*2.0 - instanceMatrix[3][0]*0.14));',
           'transformed.y += _sway + _jump;'].join('\n'));
    };
    cm.customProgramCacheKey = ()=>'crowd-v2';
    crowd = new THREE.InstancedMesh(cg, cm, crowdN);
    const dark = [0x2b3a63, 0x35466f, 0x22304f, 0x3d2f55, 0x2f4358];
    const neon = PLAYERS.map(p=>p.color);
    const c = new THREE.Color(); const m4 = new THREE.Matrix4();
    for (let i = 0; i < crowdN; i++){
      m4.makeTranslation(seatPts[i*3], seatPts[i*3+1], seatPts[i*3+2]);
      crowd.setMatrixAt(i, m4);
      if (Math.random() < 0.10) c.set(neon[(Math.random()*neon.length)|0]).multiplyScalar(0.6);
      else c.setHex(dark[(Math.random()*dark.length)|0]);
      crowd.setColorAt(i, c);
    }
    crowd.instanceMatrix.needsUpdate = true;
    if (crowd.instanceColor) crowd.instanceColor.needsUpdate = true;
    scene.add(crowd);
  }

  // ---- floodlight pylons: emissive heads + spot cones ------------------------
  const PZ = FIELD_HALF + 11;
  function pylon(x, z){
    const mast = new THREE.Mesh(new THREE.BoxGeometry(0.5, 26, 0.5),
      new THREE.MeshLambertMaterial({color: 0x2a3a6a}));
    mast.position.set(x, 13, z); scene.add(mast);
    const head = new THREE.Mesh(new THREE.BoxGeometry(2.8, 1.0, 0.5),
      new THREE.MeshStandardMaterial({color: 0x0c1224, emissive: 0xe8f3ff, emissiveIntensity: 2.6}));
    head.position.set(x, 26.2, z); head.lookAt(TRACK_LEN/2, 0, 0); scene.add(head);
    const aim = new THREE.Vector3(x*0.55 + TRACK_LEN*0.22, 0, 0);
    const s = new THREE.SpotLight(0xfff2d8, 2600, 0, 0.52, 0.65, 2);
    s.position.set(x, 25, z); s.target.position.copy(aim);
    scene.add(s, s.target);
    // faint additive cone from head to pitch — fake volumetric shaft
    const src = new THREE.Vector3(x, 25, z);
    const len = src.distanceTo(aim);
    const cone = new THREE.Mesh(new THREE.ConeGeometry(8, len, 20, 1, true),
      new THREE.MeshBasicMaterial({color: 0x9fc0ee, transparent: true, opacity: 0.028,
        blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, fog: false}));
    cone.position.copy(src.clone().add(aim).multiplyScalar(0.5));
    cone.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0), src.clone().sub(aim).normalize());
    scene.add(cone);
  }
  pylon(-2, PZ); pylon(-2, -PZ); pylon(TRACK_LEN+2, PZ); pylon(TRACK_LEN+2, -PZ);

  // ---- night sky: stars + horizon glows --------------------------------------
  {
    const N = 1200, pos = new Float32Array(N*3);
    for (let i = 0; i < N; i++){
      const a = Math.random()*Math.PI*2, e = Math.random()*Math.PI*0.42 + 0.06, R = 420;
      pos[i*3]   = TRACK_LEN/2 + R*Math.cos(e)*Math.cos(a);
      pos[i*3+1] = R*Math.sin(e);
      pos[i*3+2] = R*Math.cos(e)*Math.sin(a);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const stars = new THREE.Points(g, new THREE.PointsMaterial({color: 0xcfe0ff, size: 1.7,
      sizeAttenuation: true, transparent: true, opacity: 0.8, fog: false}));
    stars.frustumCulled = false; scene.add(stars);
    function glowSprite(hex, x, y, z, s){
      const c = document.createElement('canvas'); c.width = c.height = 128;
      const ctx = c.getContext('2d');
      const gr = ctx.createRadialGradient(64,64,0, 64,64,64);
      gr.addColorStop(0, hex); gr.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gr; ctx.fillRect(0,0,128,128);
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({map: new THREE.CanvasTexture(c),
        transparent: true, opacity: 0.20, blending: THREE.AdditiveBlending, depthWrite: false, fog: false}));
      sp.position.set(x, y, z); sp.scale.setScalar(s); scene.add(sp);
    }
    glowSprite('rgba(52,225,255,.85)',  -80, 18, -60, 190);
    glowSprite('rgba(255,78,213,.75)', TRACK_LEN + 90, 14, -70, 170);
  }

  // ---- goals: glowing frames + nets that ripple ------------------------------
  const postMat = new THREE.MeshStandardMaterial({color: 0x151a28, emissive: 0xffffff, emissiveIntensity: 1.35});
  const nets = []; // {seg, base, pos, dir, ripT}
  function goal(gx, dir){
    function post(z){
      const m = new THREE.Mesh(new THREE.CylinderGeometry(POST_R, POST_R, GOAL_H, 10), postMat);
      m.position.set(gx, GOAL_H/2, z); scene.add(m);
    }
    post(GOAL_HALF); post(-GOAL_HALF);
    const cross = new THREE.Mesh(new THREE.CylinderGeometry(POST_R, POST_R, GOAL_HALF*2, 10), postMat);
    cross.rotation.x = Math.PI/2; cross.position.set(gx, GOAL_H, 0); scene.add(cross);
    // net: sloped back panel as a line grid; sags from the crossbar down and back
    const NZ = 13, NY = 9, verts = [];
    const nodeAt = (iz, iy) => {
      const z = -GOAL_HALF + (iz/(NZ-1))*GOAL_HALF*2;
      const y = (iy/(NY-1))*GOAL_H;
      const x = gx + dir*(0.35 + (1 - y/GOAL_H)*1.6);
      return [x, y, z];
    };
    for (let iz = 0; iz < NZ; iz++) for (let iy = 0; iy < NY-1; iy++)
      verts.push(...nodeAt(iz, iy), ...nodeAt(iz, iy+1));
    for (let iy = 0; iy < NY; iy++) for (let iz = 0; iz < NZ-1; iz++)
      verts.push(...nodeAt(iz, iy), ...nodeAt(iz+1, iy));
    const pos = new Float32Array(verts);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const seg = new THREE.LineSegments(g,
      new THREE.LineBasicMaterial({color: 0xdfe8ff, transparent: true, opacity: 0.34}));
    seg.frustumCulled = false; scene.add(seg);
    nets.push({seg, base: pos.slice(), pos, dir, gx, ripT: Infinity});
  }
  goal(-GOAL_OFF, -1); goal(TRACK_LEN + GOAL_OFF, +1);
  const goalFlash = new THREE.PointLight(0xffffff, 0, 40, 2);
  goalFlash.position.set(TRACK_LEN + GOAL_OFF, 2.2, 0); scene.add(goalFlash);
  function updateNets(dt){
    for (const n of nets){
      if (n.ripT > 1.6) continue;
      n.ripT += dt/1000;
      const T = Math.min(n.ripT, 1.6), decay = Math.exp(-2.6*T);
      for (let i = 0; i < n.pos.length; i += 3){
        const dy = n.base[i+1] - 1.7, dz = n.base[i+2];
        const d = Math.hypot(dy, dz);
        n.pos[i] = n.base[i] + n.dir * decay * 0.55 * Math.sin(d*3.2 - T*16) / (1 + d*d*0.35);
      }
      n.seg.geometry.attributes.position.needsUpdate = true;
    }
  }

  function labelSprite(text, color){
    const c = document.createElement('canvas'); c.width=256; c.height=64;
    const x = c.getContext('2d');
    x.font='600 34px "Space Grotesk", sans-serif'; x.textAlign='center'; x.textBaseline='middle';
    x.lineWidth=5; x.strokeStyle='rgba(5,8,18,0.92)'; x.strokeText(text,128,34);
    x.fillStyle=color; x.fillText(text,128,34);
    const tex = new THREE.CanvasTexture(c); tex.anisotropy=4;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({map:tex, transparent:true, depthWrite:false, toneMapped:false}));
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
      new THREE.MeshBasicMaterial({map:tex, transparent:true, opacity:0.5, depthWrite:false, toneMapped:false}));
    m.rotation.x=-Math.PI/2; // lay flat on the ground (XZ plane)
    return m;
  }

  // coloured track zones — one per phase (Група 1/2/3 …), drawn along the runners' path
  const LANE_SPAN = PLAYERS.length*LANE_GAP + 2;
  (DATA.bands||[]).forEach(b=>{
    const x0=xOf(b.from), x1=xOf(b.to), w=Math.max(x1-x0, 0.2), col=new THREE.Color(b.color);
    const zone=new THREE.Mesh(new THREE.PlaneGeometry(w, LANE_SPAN),
      new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:0.10, depthWrite:false, toneMapped:false}));
    zone.rotation.x=-Math.PI/2; zone.position.set((x0+x1)/2, 0.02, 0); scene.add(zone);
    const line=new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.05, LANE_SPAN),
      new THREE.MeshBasicMaterial({color:col, transparent:true, opacity:0.45, toneMapped:false}));
    line.position.set(x1, 0.06, 0); scene.add(line);
    const lbl=floorText(b.label, b.color, w*0.92);
    lbl.position.set((x0+x1)/2, 0.08, LANE_SPAN/2 - 1.6); scene.add(lbl);
  });

  // ---- runners v3: jointed figures in a proper kit -----------------------------
  // Player colour reads as the JERSEY + SOCKS; body parts are skin, shorts are dark,
  // boots are near-black — so each runner looks like a footballer in strip, not a
  // glowing nude in trunks. Head stays the glowing player colour (no hair).
  function makeRunner(color){
    const col = new THREE.Color(color);
    const dark = col.clone().multiplyScalar(0.20);
    const jersey = new THREE.MeshStandardMaterial({color: dark, emissive: col, emissiveIntensity: 1.12, roughness: .45});
    const socks  = new THREE.MeshStandardMaterial({color: dark, emissive: col, emissiveIntensity: 0.9, roughness: .5});
    // skin keeps a small emissive so it doesn't go black in the dark neon scene
    const skin   = new THREE.MeshStandardMaterial({color: 0xd9a06b, emissive: 0x5a3517, emissiveIntensity: .35, roughness: .7});
    const shorts = new THREE.MeshStandardMaterial({color: 0x0e1428, emissive: 0x1b2748, emissiveIntensity: .5, roughness: .7});
    const boots  = new THREE.MeshStandardMaterial({color: 0x0a0c12, emissive: 0x05070c, emissiveIntensity: .3, roughness: .5, metalness: .1});
    const g = new THREE.Group();
    const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.26, 0.55, 4, 10), jersey);
    torso.position.y = 1.36; g.add(torso);
    // waistband — the shorts proper are the flared legs added over each thigh below
    const hips = new THREE.Mesh(new THREE.CapsuleGeometry(0.25, 0.16, 4, 8), shorts);
    hips.position.y = 0.99; g.add(hips);
    const head = new THREE.Mesh(new THREE.SphereGeometry(0.27, 14, 12), jersey);
    head.position.y = 1.98; g.add(head);
    // upMat/loMat clothe the two segments; shortLeg = baggy shorts over the upper thigh,
    // boot = a foot on the shin. Both ride the hip/knee groups so they follow the run cycle.
    function limb2(py, pz, upLen, loLen, r, upMat, loMat, shortLeg, boot){
      const hip = new THREE.Group(); hip.position.set(0, py, pz); g.add(hip);
      const upper = new THREE.Mesh(new THREE.CapsuleGeometry(r, upLen, 3, 6), upMat);
      upper.position.y = -(upLen/2 + r); hip.add(upper);
      if (shortLeg){
        // a flared cylinder (wider at the hem) covering the top ~half of the thigh
        const s = new THREE.Mesh(new THREE.CylinderGeometry(r*1.45, r*1.9, upLen*0.9, 10), shorts);
        s.position.y = -(upLen*0.9/2 + r*0.15);
        hip.add(s);
      }
      const knee = new THREE.Group(); knee.position.y = -(upLen + r*1.4); hip.add(knee);
      const lower = new THREE.Mesh(new THREE.CapsuleGeometry(r*0.85, loLen, 3, 6), loMat);
      lower.position.y = -(loLen/2 + r*0.85); knee.add(lower);
      if (boot){
        const b = new THREE.Mesh(new THREE.CapsuleGeometry(r*0.7, r*1.5, 3, 6), boots);
        b.rotation.z = Math.PI/2;                       // lie flat, toe pointing +x (run direction)
        b.position.set(r*1.4, -(loLen + r*1.55), 0.02); // just ahead of and below the ankle
        knee.add(b);
      }
      return {hip, knee};
    }
    // legs: skin thigh under baggy shorts + coloured sock + boot; arms: short jersey sleeve + skin forearm
    const legL = limb2(0.92,  0.15, 0.30, 0.34, 0.115, skin, socks, true, true);
    const legR = limb2(0.92, -0.15, 0.30, 0.34, 0.115, skin, socks, true, true);
    const armL = limb2(1.66,  0.33, 0.27, 0.28, 0.085, jersey, skin, false, false);
    const armR = limb2(1.66, -0.33, 0.27, 0.28, 0.085, jersey, skin, false, false);
    g.scale.setScalar(1.3);
    if (shadowsOn) g.traverse(o => { if (o.isMesh) o.castShadow = true; });
    return {g, legL, legR, armL, armR};
  }

  // blob shadows for mobile (real shadow maps are desktop-only)
  let blobTex = null;
  function blobShadow(sz){
    if (!blobTex){
      const c = document.createElement('canvas'); c.width = c.height = 64;
      const ctx = c.getContext('2d');
      const gr = ctx.createRadialGradient(32,32,2, 32,32,30);
      gr.addColorStop(0, 'rgba(0,0,0,.42)'); gr.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gr; ctx.fillRect(0,0,64,64);
      blobTex = new THREE.CanvasTexture(c);
    }
    const m = new THREE.Mesh(new THREE.PlaneGeometry(sz, sz),
      new THREE.MeshBasicMaterial({map: blobTex, transparent: true, depthWrite: false, toneMapped: false}));
    m.rotation.x = -Math.PI/2; m.position.y = 0.03; m.renderOrder = 1;
    scene.add(m); return m;
  }

  // ---- ribbon trails: additive, alpha fades to nothing at the tail -----------
  const TRAIL = 110, TRAIL_HW = 0.27;
  function makeTrail(color){
    const positions = new Float32Array(TRAIL*2*3);
    const alphas = new Float32Array(TRAIL*2);
    for (let i = 0; i < TRAIL; i++){
      const a = Math.pow(i/(TRAIL-1), 1.7)*0.7;
      alphas[i*2] = a; alphas[i*2+1] = a;
    }
    const idx = new Uint16Array((TRAIL-1)*6);
    for (let i = 0; i < TRAIL-1; i++){
      const o = i*6, v = i*2;
      idx[o]=v; idx[o+1]=v+1; idx[o+2]=v+2; idx[o+3]=v+1; idx[o+4]=v+3; idx[o+5]=v+2;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geo.setAttribute('aAlpha', new THREE.BufferAttribute(alphas, 1));
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    geo.setDrawRange(0, 0);
    const col = new THREE.Color(color);
    const mat = new THREE.ShaderMaterial({
      uniforms: {uColor: {value: new THREE.Vector3(col.r*2.1, col.g*2.1, col.b*2.1)}},
      vertexShader: 'attribute float aAlpha; varying float vA;\n' +
        'void main(){ vA = aAlpha; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }',
      fragmentShader: 'uniform vec3 uColor; varying float vA;\n' +
        'void main(){ gl_FragColor = vec4(uColor*vA, vA); }',
      transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide});
    const mesh = new THREE.Mesh(geo, mat);
    mesh.frustumCulled = false; scene.add(mesh);
    return {mesh, positions};
  }

  const runners = PLAYERS.map((p, i)=>{
    const rn = makeRunner(p.color);
    // the label lives in the scene, not on the runner — riding the rig would inherit
    // the run-cycle bob and body roll and read as text jitter
    const label = labelSprite(p.name, p.color);
    label.scale.multiplyScalar(1.3); label.position.set(0, 3.77, 0);
    scene.add(rn.g, label);
    const trail = makeTrail(p.color);
    const blob = shadowsOn ? null : blobShadow(2.0);
    return {p, rn, label, labelY: 3.77, trail, blob, filled: 0, phase: i*0.7, lastX: null, lean: 0.10};
  });

  // football dribbled in front of whoever currently leads the race — a white sphere with
  // black pentagon patches at the 12 icosahedron vertices (the classic Telstar look).
  const BALL_R = 0.45, BALL_AHEAD = 1.4;
  function makeBall(){
    const g = new THREE.Group();
    const core = new THREE.Mesh(new THREE.SphereGeometry(BALL_R, 24, 24),
      new THREE.MeshStandardMaterial({color: 0xffffff, roughness: .32, metalness: 0}));
    if (shadowsOn) core.castShadow = true;
    g.add(core);
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
  const ballBlob = shadowsOn ? null : blobShadow(1.2);
  if (ballBlob) ballBlob.visible = false;
  let ballX = null, ballZ = 0;      // ball's own glided position (lags the leader -> reads as a pass)
  let lastBX = 0, lastBZ = 0;       // previous frame position, for roll
  let shotProg = 0, shotFromX = 0, shotFromZ = 0; // finish-line shot into the net (0..1)
  let celebrate = 0;                // 0..1 ramp: crowd goes wild once the ball is through the goal

  // ---- confetti pool: ballistic particles fully integrated in the shader -----
  const CONF_N = 620, CONF_LIFE = 3.2;
  const confetti = (()=>{
    const pos0 = new Float32Array(CONF_N*3), vel = new Float32Array(CONF_N*3),
          birth = new Float32Array(CONF_N).fill(-99), colA = new Float32Array(CONF_N*3);
    const g = new THREE.BufferGeometry();
    g.setAttribute('aPos0', new THREE.BufferAttribute(pos0, 3));
    g.setAttribute('aVel', new THREE.BufferAttribute(vel, 3));
    g.setAttribute('aBirth', new THREE.BufferAttribute(birth, 1));
    g.setAttribute('aCol', new THREE.BufferAttribute(colA, 3));
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(CONF_N*3), 3)); // required by three
    const mat = new THREE.ShaderMaterial({
      uniforms: {uTime: {value: 0}, uPx: {value: renderer.getPixelRatio()}},
      vertexShader: [
        'attribute vec3 aPos0; attribute vec3 aVel; attribute float aBirth; attribute vec3 aCol;',
        'uniform float uTime; uniform float uPx; varying vec3 vCol; varying float vK;',
        'void main(){',
        '  float age = uTime - aBirth;',
        '  float k = age/' + CONF_LIFE.toFixed(2) + ';',
        '  vK = k; vCol = aCol;',
        '  if (k < 0.0 || k > 1.0){ gl_Position = vec4(0.0,0.0,-3.0,1.0); gl_PointSize = 0.0; return; }',
        '  vec3 p = aPos0 + aVel*age;',
        '  p.y -= 4.2*age*age;',
        '  p.x += 0.4*sin(age*9.0 + aBirth*13.0);',
        '  p.z += 0.4*cos(age*7.0 + aBirth*17.0);',
        '  vec4 mv = modelViewMatrix * vec4(p, 1.0);',
        '  gl_PointSize = mix(8.0, 2.5, k) * uPx * (26.0 / max(1.0, -mv.z));',
        '  gl_Position = projectionMatrix * mv;',
        '}'].join('\n'),
      fragmentShader: [
        'varying vec3 vCol; varying float vK;',
        'void main(){',
        '  if (vK < 0.0 || vK > 1.0) discard;',
        '  gl_FragColor = vec4(vCol, 1.0 - vK*vK);',
        '}'].join('\n'),
      transparent: true, depthWrite: false});
    const pts = new THREE.Points(g, mat);
    pts.frustumCulled = false; scene.add(pts);
    return {g, mat, cursor: 0, pos0, vel, birth, colA};
  })();
  let sceneT = 0;
  const confPalette = PLAYERS.map(p => new THREE.Color(p.color)).concat(
    [new THREE.Color(0x34e1ff), new THREE.Color(0xff4ed5), new THREE.Color(0xffffff)]);
  function burstConfetti(cx, cy, cz, n, power){
    for (let i = 0; i < n; i++){
      const j = confetti.cursor; confetti.cursor = (confetti.cursor + 1) % CONF_N;
      const a = Math.random()*Math.PI*2, r = Math.random();
      confetti.pos0[j*3] = cx; confetti.pos0[j*3+1] = cy; confetti.pos0[j*3+2] = cz;
      confetti.vel[j*3]   = Math.cos(a)*r*power;
      confetti.vel[j*3+1] = (2.4 + Math.random()*2.6)*(power*0.5);
      confetti.vel[j*3+2] = Math.sin(a)*r*power;
      confetti.birth[j] = sceneT + Math.random()*0.12;
      const c = confPalette[(Math.random()*confPalette.length)|0];
      confetti.colA[j*3] = c.r*1.5; confetti.colA[j*3+1] = c.g*1.5; confetti.colA[j*3+2] = c.b*1.5;
    }
    confetti.g.attributes.aPos0.needsUpdate = true;
    confetti.g.attributes.aVel.needsUpdate = true;
    confetti.g.attributes.aBirth.needsUpdate = true;
    confetti.g.attributes.aCol.needsUpdate = true;
  }
  const pendingBursts = [];

  // ---- composer: render -> bloom (linear HDR) -> output (ACES + sRGB) --------
  const composer = new EffectComposer(renderer);
  composer.addPass(new RenderPass(scene, camera));
  const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.7, 0.5, 0.85);
  composer.addPass(bloom);
  composer.addPass(new OutputPass());
  let bloomScale = isMobile ? 0.5 : 1;

  // ---- cinematic camera state -------------------------------------------------
  let introT = reduceMotion ? 1 : 0;
  const introFrom = new THREE.Vector3(-30, 24, portrait ? 20 : 26);
  const introLookFrom = new THREE.Vector3(12, 1.2, 0);
  const introTo = camera.position.clone();
  const introLookTo = controls.target.clone();
  if (introT < 1){ camera.position.copy(introFrom); controls.target.copy(introLookFrom); controls.enabled = false; }
  const killIntro = ()=>{ if (introT < 1){ introT = 1; } };
  canvas.addEventListener('pointerdown', killIntro, {passive: true});
  canvas.addEventListener('wheel', killIntro, {passive: true});
  const easeInOut = k => k < 0.5 ? 4*k*k*k : 1 - Math.pow(-2*k + 2, 3)/2;
  let driftPrevY = 0, driftPrevZ = 0;
  let finaleWas = false, savedDist = 0;   // undo the finale dolly-in when scrubbing back

  // ---- perf: one-way degrade ratchet ------------------------------------------
  let perfAcc = 0, perfN = 0, degradeLvl = 0;
  function applyResolution(){
    renderer.setPixelRatio(Math.min(devicePixelRatio, dprCap));
    composer.setPixelRatio(renderer.getPixelRatio());
    resize();
    confetti.mat.uniforms.uPx.value = renderer.getPixelRatio();
  }
  function degrade(){
    degradeLvl++;
    if (degradeLvl === 1){ bloomScale *= 0.5; resize(); }
    else if (degradeLvl === 2 && crowd){ crowd.count = Math.floor(crowd.count*0.5); }
    else if (degradeLvl === 3){
      if (sun){ sun.castShadow = false; renderer.shadowMap.enabled = false; }
      dprCap = 1.25; applyResolution();
    }
  }

  let runPhase = 0, prevLead = null, prevScored = 0, excite = 0, nextFinaleBurst = 0;
  const _v1 = new THREE.Vector3(), _v2 = new THREE.Vector3();
  tick = function(dt){
    runPhase += (dt||16) * (playing ? 0.02*SPEEDS[speedIdx] : 0.007);
    sceneT += (dt||16)/1000;
    const t = interpTotals();
    let sumX = 0;
    for (const r of runners){
      const id = r.p.id;
      const x = xOf(t[id]||0); sumX += x;
      const z = laneZ(laneIndex[id]); // fixed lane — overtakes show as forward distance only
      if (r.lastX === null) r.lastX = x;
      const spd = x - r.lastX; r.lastX = x;
      const ph = runPhase + r.phase;
      const sw = Math.sin(ph);
      // run cycle blends into a springy two-footed jump with arms thrown overhead as `celebrate` ramps up
      const run = 1 - celebrate;
      const jump = Math.abs(Math.sin(runPhase*0.9 + r.phase)) * 0.9;
      const bob = Math.abs(sw)*0.10*run + jump*celebrate;
      r.rn.g.position.set(x, bob, z);
      // forward lean grows with speed — big point jumps read as a sprint
      const targetLean = 0.10 + Math.min(0.30, Math.max(0, spd*2.2));
      r.lean += (targetLean - r.lean)*0.08;
      r.rn.g.rotation.z = -r.lean*run;
      r.rn.g.rotation.x = sw*0.04*run;
      // legs: hips swing, knee flexes as the leg recovers forward
      r.rn.legL.hip.rotation.z =  sw*0.85*run;
      r.rn.legR.hip.rotation.z = -sw*0.85*run;
      r.rn.legL.knee.rotation.z = -Math.max(0,  Math.sin(ph + Math.PI*0.5))*1.15*run - 0.08;
      r.rn.legR.knee.rotation.z = -Math.max(0, -Math.sin(ph + Math.PI*0.5))*1.15*run - 0.08;
      // arms counter-swing with a fixed elbow bend; thrown overhead in celebration
      r.rn.armL.hip.rotation.z = (-sw*0.6)*run + ( 2.7)*celebrate;
      r.rn.armR.hip.rotation.z = ( sw*0.6)*run + (-2.7)*celebrate;
      r.rn.armL.knee.rotation.z = 0.95*run + 0.15;
      r.rn.armR.knee.rotation.z = 0.95*run + 0.15;
      if (r.blob){ r.blob.position.x = x; r.blob.position.z = z; }
      // label floats above the runner: heavy low-pass kills run-cycle jitter but
      // still lets it rise gently with the celebration jump
      r.labelY += ((3.77 + bob*0.8) - r.labelY) * 0.05;
      r.label.position.set(x, r.labelY, z);
      // push torso point into the trail ribbon ring buffer (two verts per sample) —
      // only while actually moving, so a paused race keeps its trails as a motion history
      const arr = r.trail.positions, yy = 1.05 + bob;
      if (r.lastPushX === undefined || Math.abs(x - r.lastPushX) > 0.02){
        r.lastPushX = x;
        if (r.filled < TRAIL){
          const k = r.filled*6;
          arr[k]=x; arr[k+1]=yy; arr[k+2]=z-TRAIL_HW; arr[k+3]=x; arr[k+4]=yy; arr[k+5]=z+TRAIL_HW;
          r.filled++;
        } else {
          arr.copyWithin(0, 6);
          const k = (TRAIL-1)*6;
          arr[k]=x; arr[k+1]=yy; arr[k+2]=z-TRAIL_HW; arr[k+3]=x; arr[k+4]=yy; arr[k+5]=z+TRAIL_HW;
        }
        r.trail.mesh.geometry.setDrawRange(0, Math.max(0, r.filled-1)*6);
        r.trail.mesh.geometry.attributes.position.needsUpdate = true;
      }
    }
    // football glides to a spot just ahead of the current leader; on a lead change the target
    // jumps to the new lane and the ball rolls across to it — reads as a pass between players.
    // Once the race settles on its final step, the leader buries the ball in the finish net.
    let leadId = null;
    if (runners.length){
      let leadX = -Infinity;
      for (const r of runners){ const x = xOf(t[r.p.id]||0); if (x > leadX){ leadX = x; leadId = r.p.id; } }
      // confetti pops over a lead change (but not during the finale shot)
      if (prevLead !== null && leadId !== prevLead && shotProg <= 0 && leadX > 0.5){
        burstConfetti(leadX, 3.2, laneZ(laneIndex[leadId]), 80, 2.6);
        excite = Math.max(excite, 0.55);
      }
      prevLead = leadId;
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
        // two-phase strike: curl into the dead centre of the goal mouth, then blast straight through it.
        // (the leader's lane Z can be far wider than the posts, so the ball MUST converge before the line
        // or it sails wide — phase 1 guarantees bz=0 exactly at the goal line.)
        const goalX = TRACK_LEN + GOAL_OFF, endX = goalX + 16;
        const eg = 0.45; // share of the shot spent reaching the line; the rest is the fly-through
        if (shotProg <= eg){
          const k = shotProg / eg;
          bx = shotFromX + (goalX - shotFromX) * k;
          bz = shotFromZ * (1 - k);                       // converge to centre exactly at the line
          by = BALL_R + Math.sin(Math.PI*0.5*k) * 1.3;    // ~1.75 high at the line, well under the crossbar
        } else {
          const k = (shotProg - eg) / (1 - eg);
          bx = goalX + 1.55 * Math.min(1, k*2.2);         // bury it in the sagging net, not through it
          bz = 0;
          by = (BALL_R + 1.3) - k * 1.0;                  // drop into the rippling net
        }
        ballX = bx; ballZ = bz;
      }
      // crowd erupts the instant the ball crosses the goal line; smooth ramp so the jump kicks in cleanly
      const scored = shotProg > 0 && bx >= (TRACK_LEN + GOAL_OFF - 0.3) ? 1 : 0;
      if (scored === 1 && prevScored === 0){
        nets[1].ripT = 0;                        // net ripple
        goalFlash.intensity = 900;               // white pop at the goal mouth
        burstConfetti(TRACK_LEN + GOAL_OFF - 1, 2.6, 0, 160, 3.4);
        nextFinaleBurst = sceneT + 0.5;
      }
      prevScored = scored;
      // the party keeps going for as long as the race sits on its final step
      if (celebrate > 0.5 && sceneT >= nextFinaleBurst){
        nextFinaleBurst = sceneT + 0.75 + Math.random()*0.5;
        const gx = TRACK_LEN + GOAL_OFF;
        burstConfetti(gx - 3 - Math.random()*9, 2.5 + Math.random()*2, (Math.random()-0.5)*12, 90, 2.9);
      }
      celebrate += (scored - celebrate) * 0.06;
      ball.visible = true;
      ball.position.set(bx, by, bz);
      if (ballBlob){ ballBlob.visible = true; ballBlob.position.x = bx; ballBlob.position.z = bz; }
      const dx = bx - lastBX, dz = bz - lastBZ, dist = Math.hypot(dx, dz);
      if (dist > 1e-4){ _v1.set(dz, 0, -dx).normalize(); ball.rotateOnWorldAxis(_v1, dist/BALL_R); } // roll
      lastBX = bx; lastBZ = bz;
    }
    // scheduled finale bursts
    while (pendingBursts.length && pendingBursts[0].t <= sceneT){
      const b = pendingBursts.shift();
      burstConfetti(b.x, b.y, b.z, 90, 2.8);
    }
    confetti.mat.uniforms.uTime.value = sceneT;
    goalFlash.intensity *= Math.pow(0.93, (dt||16)/16);
    updateNets(dt||16);
    // crowd: idle sway always; jumps on celebration or a lead-change flash of excitement
    excite = Math.max(0, excite - (dt||16)/2600);
    crowdUni.uTime.value = sceneT;
    crowdUni.uJump.value = Math.max(celebrate, excite);
    // keep the camera framing the moving pack
    const meanX = runners.length ? sumX/runners.length : TRACK_LEN/2;
    if (sun){ sun.position.x = meanX + 14; sun.target.position.x = meanX; }
    if (introT < 1){
      // intro fly-in: high behind the start goal, easing into the side view
      introT = Math.min(1, introT + (dt||16)/2500);
      const e = easeInOut(introT);
      camera.position.lerpVectors(introFrom, introTo, e);
      controls.target.lerpVectors(introLookFrom, introLookTo, e);
      if (introT >= 1) controls.enabled = true;
    } else if (!userInteracting){
      if (celebrate > 0.2 && leadId){
        // finale: glide in front of the winner so the lit stadium fills the background
        if (!finaleWas){ finaleWas = true; savedDist = camera.position.distanceTo(controls.target); }
        const wz = laneZ(laneIndex[leadId]);
        const wx = xOf(t[leadId]||0);
        _v1.set(wx, 1.8, wz);
        controls.target.lerp(_v1, 0.03);
        _v2.set(wx + 12 + Math.sin(sceneT*0.28)*3, 6.8 + Math.sin(sceneT*0.2)*1.1, wz + 13 + Math.cos(sceneT*0.28)*3);
        camera.position.lerp(_v2, 0.028);
      } else {
        // scrubbed back out of the finale: ease the camera back to its pre-finale distance
        if (finaleWas){
          _v2.copy(camera.position).sub(controls.target);
          const len = _v2.length(), want = len + (savedDist - len)*0.04;
          camera.position.copy(controls.target).add(_v2.multiplyScalar(want/len));
          if (Math.abs(savedDist - len) < 0.8) finaleWas = false;
        }
        // follow the pack by PANNING — shift target and camera by the same delta — so the user's own
        // rotation/zoom is preserved; skip entirely while they're dragging so the gesture isn't fought.
        const dxPan = (meanX - controls.target.x) * 0.05;
        controls.target.x += dxPan;
        camera.position.x += dxPan;
        if (!reduceMotion){
          // idle drift: a slow breathing of the camera so the frame never feels frozen
          const dy = Math.sin(sceneT*0.30)*0.8, dz = Math.cos(sceneT*0.21)*1.1;
          camera.position.y += dy - driftPrevY; camera.position.z += dz - driftPrevZ;
          driftPrevY = dy; driftPrevZ = dz;
        }
      }
    }
    controls.update();
    // one-way perf ratchet: if a rolling window averages worse than ~38 fps, shed cost
    perfAcc += (dt||16); perfN++;
    if (perfN >= 120){
      const avg = perfAcc/perfN; perfAcc = 0; perfN = 0;
      if (avg > 26 && degradeLvl < 3) degrade();
    }
    composer.render();
  };

  function resize(){
    camera.aspect = innerWidth/innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    composer.setSize(innerWidth, innerHeight);
    bloom.setSize(innerWidth*bloomScale, innerHeight*bloomScale);
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

    generated_at = datetime.now(PRAGUE).strftime("%d.%m.%Y %H:%M")
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
