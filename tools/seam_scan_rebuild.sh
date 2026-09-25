#!/usr/bin/env bash
# Conflict-recovery callback for seam-scan.yml, passed to git_push_retry.sh.
# Invoked only after a genuine content conflict on the cron's own generated
# artifacts (task 1744, BUILDLOG.md) -- the caller has already reset the
# checkout to the new origin/<branch> tip. This regenerates the exact same
# artifacts the workflow's earlier steps built (scan -> seal -> report ->
# streak -> audit -> badge -> card), fresh against that new tip, then stages
# and commits them again. Re-sealing is correct here, not a fallback: an
# hourly rescan on unchanged state already seals a fresh entry every run (the
# tablet records that the scan ran, not only that something changed) -- so
# rebuilding after a conflict seals the noon cron's own observation instead
# of silently losing it, which is what plain rebase failure used to do.
#
# Must be run from the repo root, matching the workflow's own steps.
set -euo pipefail

today="$(date -u +%F)"

(
  cd fencepost
  export PYTHONPATH="seam_engine/src"
  mkdir -p candidates
  python3 -m seam_engine.scan "candidates/${today}.json"
  python3 -m seam_engine.ledger append "candidates/${today}.json"
  python3 -m seam_engine.ledger verify
  python3 -m seam_engine.report --write
  python3 -m seam_engine.streak status
  python3 -m seam_engine.audit --write || true
  python3 -m seam_engine.badge --write || true
)
python3 tools/report_card.py latest || true

git config user.name "Off-By-One"
git config user.email "off-by-one@orita.gods"
git add fencepost/candidates fencepost/GAPS fencepost/REPORTS fencepost/AUDIT.md fencepost/BADGE.json docs/fencepost/reports

if git diff --cached --quiet; then
  echo "nothing to reseal after rebuild -- origin already carries an equivalent tablet for ${today}"
  exit 0
fi

git commit -m "seam-scan: ${today} tablet sealed, report rendered (automatic, no human trigger, rebuilt after push conflict)"
