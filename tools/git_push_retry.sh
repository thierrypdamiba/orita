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
set -euo pipefail

branch="$(git rev-parse --abbrev-ref HEAD)"

for attempt in 1 2 3 4 5; do
  if git push; then
    exit 0
  fi
  echo "git push rejected (attempt ${attempt}/5) -- fetching + rebasing onto origin/${branch} and retrying" >&2
  git fetch origin "${branch}"
  git rebase "origin/${branch}"
  sleep $((attempt * 2))
done

echo "git push failed after 5 attempts" >&2
exit 1
