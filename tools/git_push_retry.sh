#!/usr/bin/env bash
# Retries a plain `git push` against a fetch+rebase when the remote moved
# first. Every cron workflow (seam-scan, oracle-cadence) commits and pushes
# on its own schedule, and the noon-UTC seam-scan run can land mid-flight of
# the hourly ritual's own commits -- a real, observed race, not a
# hypothetical one: seam-scan's 2026-08-18T12:41Z run built and committed
# today's report locally, then lost the push outright to a concurrent
# hourly-ritual commit and exited non-zero with the report silently
# discarded (task 847, orita BUILDLOG). A plain `git push` has no recovery
# from that; this retries a bounded number of times before giving up loudly.
#
# A second, distinct race showed up live at 2026-09-25T16:35Z (task 1744):
# the rejected push was for a REGENERATED file both the cron and the hourly
# ritual write independently (fencepost/GAPS/<today>.md) -- a real CONTENT
# conflict, not just a stale ref. A plain rebase can't resolve that (there is
# no "ours"/"theirs" that's correct; both sides are a valid tablet seal, the
# rebase just can't tell). Left as `set -euo pipefail` had it before, that
# conflict killed the whole run and the cron's observation was silently
# lost -- nothing sealed, nothing pushed, nothing recorded anywhere.
#
# Usage: git_push_retry.sh [rebuild-script]
#   rebuild-script (optional): a script that, given a clean checkout already
#   reset to the new origin tip, regenerates the SAME derived artifacts this
#   caller committed, `git add`s them, and `git commit`s again (it owns its
#   own commit message). Called only when the rebase failure is a genuine
#   content conflict, never on a plain non-conflicting divergence (that case
#   still resolves via ordinary rebase, as before). Without it, a content
#   conflict still fails loud exactly as before -- this is opt-in, backward
#   compatible with every existing call site.
set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"
rebuild_script="${1:-}"

for attempt in 1 2 3 4 5; do
  if git push; then
    exit 0
  fi
  echo "git push rejected (attempt ${attempt}/5) -- fetching + rebasing onto origin/${branch} and retrying" >&2
  git fetch origin "${branch}"

  if git rebase "origin/${branch}"; then
    sleep $((attempt * 2))
    continue
  fi

  # Rebase failed. Distinguish a genuine content conflict (unmerged paths)
  # from anything else -- only a real conflict gets the rebuild-and-recommit
  # treatment; any other rebase failure falls through to the old loud-fail
  # behavior so we never mask a real problem as "just a conflict".
  if [ -n "$(git status --porcelain=v1 | grep -E '^(UU|AA|DD|AU|UA|UD|DU) ')" ]; then
    if [ -z "${rebuild_script}" ]; then
      echo "content conflict on rebase and no rebuild-script given -- failing loud (as before)" >&2
      git rebase --abort
      exit 1
    fi
    echo "content conflict on regenerable artifacts -- abandoning this rebase, resetting to origin/${branch}, and rebuilding fresh via ${rebuild_script}" >&2
    git rebase --abort
    git reset --hard "origin/${branch}"
    bash "${rebuild_script}"
    sleep $((attempt * 2))
    continue
  fi

  echo "rebase failed for a reason other than a content conflict -- failing loud" >&2
  exit 1
done

echo "git push failed after 5 attempts" >&2
exit 1
