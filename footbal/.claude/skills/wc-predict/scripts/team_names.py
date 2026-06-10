#!/usr/bin/env python3
"""Shared team-name normalization for matching across data sources.

Sources disagree on national-team names (Czechia vs Czech Republic, Türkiye vs Turkey,
Bosnia-Herzegovina vs Bosnia and Herzegovina, USA vs United States, ...). normalize()
collapses every known spelling of a team to one canonical lowercase key so two artifacts
can be matched reliably. Pure stdlib; imported by elo.py and generate_dashboard.py.
"""

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
