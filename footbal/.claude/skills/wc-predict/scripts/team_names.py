#!/usr/bin/env python3
"""Shared team-name normalization for matching across data sources.

Sources disagree on national-team names (Czechia vs Czech Republic, Türkiye vs Turkey,
Bosnia-Herzegovina vs Bosnia and Herzegovina, USA vs United States, ...). normalize()
collapses every known spelling of a team to one canonical lowercase key so two artifacts
can be matched reliably. report_filename() turns a match into its deterministic per-match
report name so re-predicting overwrites in place instead of accumulating timestamped files.
Pure stdlib; imported by elo.py, generate_report.py and generate_dashboard.py.
"""

import re
import unicodedata

# variant (lowercased) -> canonical key. Names not listed normalize to their own
# lowercased/whitespace-collapsed form, so the canonical names below need no entry.
ALIASES = {
    "czechia": "czech republic",
    "türkiye": "turkey",
    "turkiye": "turkey",
    "korea republic": "south korea",
    "republic of korea": "south korea",
    "usa": "united states",
    "u.s.a.": "united states",
    "united states of america": "united states",
    "bosnia and herzegovina": "bosnia",
    "bosnia-herzegovina": "bosnia",
    "bosnia & herzegovina": "bosnia",
    "côte d'ivoire": "ivory coast",
    "cote d'ivoire": "ivory coast",
    "curaçao": "curacao",
    "ir iran": "iran",
    "iran islamic republic": "iran",
}


def normalize(name):
    """Canonical lowercase key for a team name, applying the alias table."""
    if not name:
        return ""
    n = " ".join(str(name).strip().lower().split())
    return ALIASES.get(n, n)


def same_team(a, b):
    return normalize(a) == normalize(b)


def slug(name):
    """Filesystem-safe slug from a team name: canonical key, diacritics stripped,
    non-alphanumeric runs collapsed to single hyphens."""
    n = unicodedata.normalize("NFKD", normalize(name))
    n = "".join(c for c in n if not unicodedata.combining(c))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", n)).strip("-")


def match_date(kickoff):
    """UTC date (YYYY-MM-DD) from an ISO kickoff like '2026-06-11T19:00:00Z'.
    Returns 'tbd' when the kickoff is missing or unparseable."""
    if not kickoff:
        return "tbd"
    s = str(kickoff).strip()
    m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else "tbd"


def report_filename(home, away, kickoff):
    """Deterministic per-match report basename, e.g.
    'wc-report-2026-06-11-mexico-vs-south-africa.html'. The same (home, away, kickoff)
    always yields the same name, so re-predicting a match overwrites its single file."""
    return f"wc-report-{match_date(kickoff)}-{slug(home)}-vs-{slug(away)}.html"
