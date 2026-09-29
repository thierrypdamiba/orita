#!/usr/bin/env bash
# Generic conflict-recovery callback for oracle-cadence.yml's per-cadence
# commit steps, passed to git_push_retry.sh. records/ledger.jsonl is an
# append-only hash-chained file every cadence-commit step in this workflow
# (and the hourly ritual's own separate Nisaba ledger append) writes to --
# two independent appends at the same tail position are a genuine content
# conflict no plain rebase can resolve (there is no "ours"/"theirs" that's
# correct; both sides are a real, timestamped, already-computed call). Left
# unhandled, the step failed loud and the sealed call was lost outright:
# observed live 2026-09-29T18:25Z, oracle-cadence run 36611866069, the
# cadence step's own hash 027a1b23...898 sealed and chain-verified, then
# dropped when the push rebase hit this exact conflict with no rebuild-
# script wired in to recover it (git_push_retry.sh had shipped the recovery
# mechanism itself two tasks earlier for seam-scan's identical race, but
# oracle-cadence's ~50 commit steps were never wired to use it).
#
# Usage: oracle_rebuild.sh <module> <date-mode> <file...>
#   module: the oracle_engine submodule to rerun (e.g. cadence, autograde,
#     star_cadence, tag_autograde) -- exactly the module the original step
#     ran. Reran fresh against the new origin tip this is correct, not a
#     fallback: append() computes its hash from the CURRENT chain tip, so
#     a fresh call is a fresh, validly-chained, differently-hashed
#     prediction -- never a stale replay of the one that got lost.
#   date-mode: "backdate" to pin GIT_AUTHOR_DATE/GIT_COMMITTER_DATE to
#     today's 03:00 UTC, matching the original step's own Nyx/Zashiki
#     window discipline (TOWN-OPERATIONS.md Iron rule 7); "-" to leave the
#     commit at the real wall-clock time, matching every other step.
#   file...: paths to git add, the same as the original step's own git add
#     line (records/ledger.jsonl, plus a snapshot file where one exists).
#
# Called only after a genuine content conflict; git_push_retry.sh has
# already reset the checkout to the new origin tip before invoking this.
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: oracle_rebuild.sh <module> <date-mode> <file...>" >&2
  exit 1
fi

module="$1"
date_mode="$2"
shift 2

today="$(date -u +%F)"
PYTHONPATH="oracle/oracle_engine/src" python3 -m "oracle_engine.${module}"
python3 tools/ledger.py verify

for f in "$@"; do
  if [ -f "${f}" ]; then
    git add "${f}"
  fi
done
if git diff --cached --quiet; then
  echo "nothing to reseal after rebuild -- origin already carries an equivalent call for ${today}"
  exit 0
fi

if [ "${date_mode}" = "backdate" ]; then
  export GIT_AUTHOR_DATE="${today}T03:00:00Z"
  export GIT_COMMITTER_DATE="${today}T03:00:00Z"
fi
git commit -m "oracle-${module}: ${today} call sealed (automatic, no human trigger, rebuilt after push conflict)"
