#!/usr/bin/env python3
"""Predict the most probable football scoreline from bookmaker odds.

Approach:
  1. Convert decimal 1X2 odds to implied probabilities and remove the
     bookmaker margin with the power method (solve k in sum((1/o)^k)=1).
     This shades longshots more than favourites, matching how books price.
  2. Fit a Dixon-Coles goals model: expected goals (lambda_home, lambda_away)
     plus a low-score correlation rho whose win/draw/win probabilities match
     the de-margined 1X2 odds. With Over/Under 2.5 odds supplied, rho is also
     fitted so the total-goals level matches too (3 params / 3 targets — the
     1X2 calibration stays exact). Without O/U, rho is fixed to a prior so the
     0-0/1-1 split still reflects football's empirical draw clustering.
  3. Rank every scoreline by probability, and rank candidate predictions
     by expected points under the prediction-game scoring rules
     (points for exact score vs points for correct outcome).

Pure Python 3, no dependencies.

Examples:
  predict_score.py --home Mexico --away "South Africa" --odds 1.65 3.6 5.5
  predict_score.py --odds 1.65 3.6 5.5 --over25 1.9 --under25 1.9 --json
"""

import argparse
import json
import math
import sys

MAX_GOALS = 15         # grid for fitting AND reporting (covers lambda up to ~4.5)
TABLE_MAX_GOALS = 6    # scorelines shown/ranked (covers >99.9% of mass)
DEFAULT_RHO = -0.08    # Dixon-Coles low-score correction prior when no O/U is given
                       # (references/historical-scores.md: 1-1 10.5% > 0-0 8.0% in modern WCs)
LAMBDA_MAX = 8.0       # sanity bound for directly-supplied --lambdas


def poisson_pmf_vec(lam, n):
    """P(X=k) for k in 0..n, built iteratively to avoid factorial overflow."""
    out = [math.exp(-lam)]
    for k in range(1, n + 1):
        out.append(out[-1] * lam / k)
    return out


def dc_tau(i, j, lam_h, lam_a, rho):
    """Dixon-Coles correction multiplier for the four low-score cells."""
    if i == 0 and j == 0:
        return 1.0 - lam_h * lam_a * rho
    if i == 0 and j == 1:
        return 1.0 + lam_h * rho
    if i == 1 and j == 0:
        return 1.0 + lam_a * rho
    if i == 1 and j == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lam_home, lam_away, rho, max_goals):
    """Joint scoreline probabilities, Dixon-Coles-corrected and renormalised."""
    ph = poisson_pmf_vec(lam_home, max_goals)
    pa = poisson_pmf_vec(lam_away, max_goals)
    m = [[ph[i] * pa[j] for j in range(max_goals + 1)] for i in range(max_goals + 1)]
    if rho:
        for i in (0, 1):
            for j in (0, 1):
                m[i][j] *= dc_tau(i, j, lam_home, lam_away, rho)
    s = sum(map(sum, m))
    return [[x / s for x in row] for row in m]


def outcome_probs(matrix):
    home = draw = away = over25 = 0.0
    n = len(matrix)
    for i in range(n):
        for j in range(n):
            p = matrix[i][j]
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
            if i + j >= 3:
                over25 += p
    return home, draw, away, over25


TOTALS_LADDER = (0.5, 1.5, 2.5, 3.5, 4.5)


def market_implications(matrix):
    """Model-implied probabilities for the same markets bookmakers quote, so the
    scoreline sheet can be cross-checked against btts / over-under consensus.
    Returns btts_yes and P(total > line) for each ladder line."""
    n = len(matrix)
    btts_yes = 0.0
    over = {line: 0.0 for line in TOTALS_LADDER}
    for i in range(n):
        for j in range(n):
            p = matrix[i][j]
            if i >= 1 and j >= 1:
                btts_yes += p
            for line in TOTALS_LADDER:
                if i + j > line:
                    over[line] += p
    return btts_yes, over


def _outcome_from_vecs(ph, pa, lam_h, lam_a, rho):
    """home/draw/away/over2.5 from precomputed pmf vectors (fast inner loop for fitting)."""
    home = draw = away = over25 = total = 0.0
    n = len(ph)
    for i in range(n):
        phi = ph[i]
        for j in range(n):
            p = phi * pa[j]
            if rho and i <= 1 and j <= 1:
                p *= dc_tau(i, j, lam_h, lam_a, rho)
            total += p
            if i + j >= 3:
                over25 += p
            if i > j:
                home += p
            elif i == j:
                draw += p
            else:
                away += p
    return home / total, draw / total, away / total, over25 / total


def _fit_lambdas_1x2(p_home, p_away, rho):
    """Coarse-to-fine 2D grid for (lambda_home, lambda_away) matching the 1X2 outcome
    probabilities at a fixed rho."""
    lo_h, hi_h = 0.05, 4.5
    lo_a, hi_a = 0.05, 4.5
    best = (float("inf"), 1.3, 1.3)
    for _ in range(4):
        steps = 22
        local = None
        for i in range(steps + 1):
            lh = lo_h + (hi_h - lo_h) * i / steps
            ph = poisson_pmf_vec(lh, MAX_GOALS)
            for j in range(steps + 1):
                la = lo_a + (hi_a - lo_a) * j / steps
                pa = poisson_pmf_vec(la, MAX_GOALS)
                h, _, a, _ = _outcome_from_vecs(ph, pa, lh, la, rho)
                err = (h - p_home) ** 2 + (a - p_away) ** 2
                if local is None or err < local[0]:
                    local = (err, lh, la)
        best = local
        span_h = (hi_h - lo_h) / steps * 2
        span_a = (hi_a - lo_a) / steps * 2
        lo_h, hi_h = max(0.01, best[1] - span_h), best[1] + span_h
        lo_a, hi_a = max(0.01, best[2] - span_a), best[2] + span_a
    return best[1], best[2]


def fit_lambdas(p_home, p_away, p_over25=None, rho=None):
    """Fit (lambda_home, lambda_away, rho).

    1X2 is matched exactly by construction: for any rho the two lambdas are solved to the
    de-margined H/A. When O/U is supplied (and rho not pinned), rho is then chosen so the
    total-goals level (P over 2.5) best matches the market — so totals refine only the
    within-outcome scoreline split, never the dominant 1X2 outcome probabilities. Without
    O/U, rho is the fixed prior (or a user override)."""
    if rho is None and p_over25 is not None:
        lo_r, hi_r = -0.20, 0.0
        best = None
        for _ in range(2):
            rsteps = 10
            local = None
            for k in range(rsteps + 1):
                r = lo_r + (hi_r - lo_r) * k / rsteps
                lh, la = _fit_lambdas_1x2(p_home, p_away, r)
                _, _, _, o = _outcome_from_vecs(poisson_pmf_vec(lh, MAX_GOALS),
                                                poisson_pmf_vec(la, MAX_GOALS), lh, la, r)
                err = (o - p_over25) ** 2
                if local is None or err < local[0]:
                    local = (err, r, lh, la)
            best = local
            span = (hi_r - lo_r) / rsteps * 2
            lo_r, hi_r = max(-0.20, best[1] - span), min(0.0, best[1] + span)
        return best[2], best[3], best[1]
    rho_fixed = DEFAULT_RHO if rho is None else rho
    lh, la = _fit_lambdas_1x2(p_home, p_away, rho_fixed)
    return lh, la, rho_fixed


def demargin_power(odds):
    """Remove bookmaker margin via the power method: solve k with sum((1/o)^k)=1.
    Shades longshots more than favourites (fixes proportional underrating of favourites)."""
    inv = [1.0 / o for o in odds]
    lo, hi = 0.5, 2.0
    for _ in range(60):
        k = (lo + hi) / 2
        s = sum(v ** k for v in inv)
        if s > 1.0:
            lo = k
        else:
            hi = k
    k = (lo + hi) / 2
    fair = [v ** k for v in inv]
    t = sum(fair)
    return [x / t for x in fair]


def outcome_of(i, j):
    return "home" if i > j else ("away" if j > i else "draw")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", default="Home", help="home / first-listed team name")
    ap.add_argument("--away", default="Away", help="away / second-listed team name")
    ap.add_argument("--odds", nargs=3, type=float, metavar=("HOME", "DRAW", "AWAY"),
                    help="decimal 1X2 odds, e.g. --odds 1.65 3.6 5.5")
    ap.add_argument("--lambdas", nargs=2, type=float, metavar=("HOME", "AWAY"),
                    help="expected goals directly (skips odds fitting); use when odds are "
                         "unavailable, e.g. from goal averages: lam_A=(scored_A+conceded_B)/2")
    ap.add_argument("--over25", type=float, help="decimal odds for Over 2.5 goals (use WITH --under25)")
    ap.add_argument("--under25", type=float, help="decimal odds for Under 2.5 goals (use WITH --over25)")
    ap.add_argument("--rho", type=float, default=None,
                    help=f"Dixon-Coles low-score correlation; default fits from O/U when given, "
                         f"else uses the prior {DEFAULT_RHO}")
    ap.add_argument("--points-exact", type=float, default=8,
                    help="game points for exact score (default 8; the user's pool: 8 group / 16 playoff)")
    ap.add_argument("--points-outcome", type=float, default=5,
                    help="game points for correct outcome only (default 5; pool: 5 group / 10 playoff). "
                         "Playoff doubling keeps the 8:5 ratio, so the optimal pick is unchanged")
    ap.add_argument("--top", type=int, default=7, help="how many top scorelines to list")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    if not args.odds and not args.lambdas:
        sys.exit("error: provide --odds H D A or --lambdas H A")

    if (args.over25 is None) != (args.under25 is None):
        sys.exit("error: --over25 and --under25 must be given together (a lone totals price "
                 "cannot be de-margined and would be silently ignored)")

    margin = p_home = p_draw = p_away = p_over25 = None
    if args.odds:
        oh, od, oa = args.odds
        if min(oh, od, oa) <= 1.0:
            sys.exit("error: decimal odds must be > 1.0")
        margin = sum(1 / x for x in (oh, od, oa)) - 1
        p_home, p_draw, p_away = demargin_power((oh, od, oa))

        if args.over25 is not None:
            if min(args.over25, args.under25) <= 1.0:
                sys.exit("error: over/under odds must be > 1.0")
            o_over, o_under = demargin_power((args.over25, args.under25))
            p_over25 = o_over

        lam_h, lam_a, rho = fit_lambdas(p_home, p_away, p_over25, rho=args.rho)
    else:
        lam_h, lam_a = args.lambdas
        if not (0 < lam_h <= LAMBDA_MAX) or not (0 < lam_a <= LAMBDA_MAX):
            sys.exit(f"error: --lambdas must be in (0, {LAMBDA_MAX:g}] "
                     f"(got {lam_h} {lam_a}); check for a sign or transposition typo")
        rho = args.rho if args.rho is not None else DEFAULT_RHO

    matrix = score_matrix(lam_h, lam_a, rho, MAX_GOALS)
    m_home, m_draw, m_away, m_over = outcome_probs(matrix)
    outcome_p = {"home": m_home, "draw": m_draw, "away": m_away}
    m_btts, m_over_ladder = market_implications(matrix)

    scorelines = [(i, j, matrix[i][j])
                  for i in range(TABLE_MAX_GOALS + 1)
                  for j in range(TABLE_MAX_GOALS + 1)]
    # deterministic order: probability desc, then fewer goals / tighter margin / home-leaning
    scorelines.sort(key=lambda r: (-r[2], r[0] + r[1], abs(r[0] - r[1]), -r[0]))

    # expected game points for predicting scoreline (i, j):
    # exact hit pays points_exact; same outcome but different score pays points_outcome
    ev = [(i, j, p,
           p * args.points_exact + (outcome_p[outcome_of(i, j)] - p) * args.points_outcome)
          for i, j, p in scorelines]
    ev.sort(key=lambda r: (-r[3], -r[2], r[0] + r[1], abs(r[0] - r[1]), -r[0]))
    rec = ev[0]

    if args.json:
        print(json.dumps({
            "home": args.home, "away": args.away,
            "odds": {"home": oh, "draw": od, "away": oa} if args.odds else None,
            "over_under_25_odds": ({"over": args.over25, "under": args.under25}
                                   if args.over25 is not None else None),
            "bookmaker_margin": round(margin, 4) if margin is not None else None,
            "implied_probabilities": {"home": round(p_home, 4), "draw": round(p_draw, 4),
                                      "away": round(p_away, 4)} if p_home is not None else None,
            "expected_goals": {"home": round(lam_h, 3), "away": round(lam_a, 3)},
            "dixon_coles_rho": round(rho, 4),
            "scoring": {"exact": args.points_exact, "outcome": args.points_outcome},
            "model_outcome_probabilities": {"home": round(m_home, 4), "draw": round(m_draw, 4),
                                            "away": round(m_away, 4), "over_2_5": round(m_over, 4)},
            "model_market_implications": {
                "btts_yes": round(m_btts, 4),
                "over": {str(line): round(p, 4) for line, p in m_over_ladder.items()},
            },
            "top_scorelines": [{"score": f"{i}-{j}", "probability": round(p, 4), "outcome": outcome_of(i, j)}
                               for i, j, p in scorelines[:args.top]],
            "recommendation": {"score": f"{rec[0]}-{rec[1]}", "probability": round(rec[2], 4),
                               "expected_points": round(rec[3], 3)},
            "alternatives": [{"score": f"{i}-{j}", "probability": round(p, 4), "expected_points": round(e, 3)}
                             for i, j, p, e in ev[1:4]],
        }, ensure_ascii=False, indent=2))
        return

    fav = max(outcome_p, key=outcome_p.get)
    fav_name = {"home": args.home, "away": args.away, "draw": "Draw"}[fav]
    print(f"{args.home} vs {args.away}")
    if args.odds:
        print(f"  odds {oh} / {od} / {oa}   (bookmaker margin {margin:.1%})")
        print(f"  implied probabilities: {args.home} {p_home:.1%} | draw {p_draw:.1%} | {args.away} {p_away:.1%}")
    print(f"  expected goals: {args.home} {lam_h:.2f} — {args.away} {lam_a:.2f}   (Dixon-Coles rho {rho:+.3f})")
    print(f"  most likely outcome: {fav_name} ({outcome_p[fav]:.1%})")
    print()
    print(f"  top {args.top} scorelines:")
    for i, j, p in scorelines[:args.top]:
        print(f"    {i}-{j}  {p:6.1%}  ({outcome_of(i, j)})")
    print()
    print(f"  RECOMMENDED PREDICTION: {rec[0]}-{rec[1]}"
          f"   (P(exact) {rec[2]:.1%}, expected points {rec[3]:.2f}"
          f" @ {args.points_exact:g}/{args.points_outcome:g} scoring)")
    alts = ", ".join(f"{i}-{j} (EV {e:.2f})" for i, j, p, e in ev[1:4])
    print(f"  alternatives: {alts}")


if __name__ == "__main__":
    main()
