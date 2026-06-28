#!/usr/bin/env bash
# Local/CI runner for the automated pool update: gate -> render -> deploy ONLY on change.
# Mirrors .github/workflows/pool-auto.yml so the whole flow can be tested locally.
#
# Usage:
#   pool_auto.sh                gate + render, then deploy footbal/pool to gh-pages if changed
#   pool_auto.sh --no-deploy    gate + render only, never push (safe — use this to test)
#   pool_auto.sh --force        skip the change gate, always re-render (and deploy unless --no-deploy)
#
# Token: POOL_API_TOKEN from the environment or footbal/.env (same as pool_spy.py).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts -> pool-spy -> skills -> .claude -> footbal
FOOTBAL_DIR="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

DEPLOY=1
FORCE=""
for arg in "$@"; do
  case "$arg" in
    --no-deploy|--dry-run) DEPLOY=0 ;;
    --force) FORCE="--force" ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

cd "$FOOTBAL_DIR"

PREV="$(mktemp)"
GH_OUT="$(mktemp)"
trap 'rm -f "$PREV" "$GH_OUT"' EXIT

# previous state straight from gh-pages (exact branch content, no CDN lag). FETCH_HEAD is
# the freshly fetched gh-pages tip — reliable even in CI where origin/gh-pages isn't tracked.
git fetch origin gh-pages --depth=1 >/dev/null 2>&1 || true
git show FETCH_HEAD:footbal/pool/.state.json > "$PREV" 2>/dev/null \
  || git show origin/gh-pages:footbal/pool/.state.json > "$PREV" 2>/dev/null \
  || echo '{}' > "$PREV"

# render (gated) — pool_auto.py writes changed=true|false to $GH_OUT
python3 .claude/skills/pool-spy/scripts/pool_auto.py \
  --prev-state "$PREV" \
  --github-output "$GH_OUT" \
  $FORCE

changed="$(grep -E '^changed=' "$GH_OUT" | tail -1 | cut -d= -f2 || true)"

if [ "$changed" != "true" ]; then
  echo "pool-auto: no changes — nothing to deploy."
  exit 0
fi

if [ "$DEPLOY" != "1" ]; then
  echo "pool-auto: changes detected — skipping deploy (--no-deploy)."
  exit 0
fi

echo "pool-auto: changes detected — deploying footbal/pool to gh-pages…"
# GH_PAGES_REPO lets CI pass an authenticated https URL (gh-pages clones afresh and would
# otherwise have no credentials). Local runs leave it unset and push over the SSH origin.
# A git URL has no spaces, so the unquoted ${VAR:+…} expansion is safe under `set -u`.
npx -y gh-pages@6 -d pool -e footbal/pool --add --dotfiles \
  ${GH_PAGES_REPO:+-r $GH_PAGES_REPO} \
  -m "auto: update pool $(date -u +%FT%TZ)"
echo "pool-auto: deployed → https://alexmost.github.io/AI-work-place/footbal/pool/"
