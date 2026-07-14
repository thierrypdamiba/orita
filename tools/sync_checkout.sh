#!/usr/bin/env bash
# tools/sync_checkout.sh <repo-dir> [branch]
#
# Task 58. Kothar-wa-Khasis's fix for a bug nobody filed because everyone
# just... fixed it by hand. Three hours running, a fresh session's
# checkout of ~/orita or ~/orita-vault landed in detached HEAD, and three
# hours running the recovery was the same judgment call re-reasoned from
# scratch: is origin/main a clean ancestor of this detached HEAD, and if
# so, which way do I rebuild main so nothing gets lost? You already knew
# the answer. You've known it since 04:0x. This just runs it.
#
# Never destroys work. Four cases, in order:
#   1. Already on a branch -> no-op.
#   2. HEAD == origin/<branch>            -> branch tracks origin, clean.
#   3. origin/<branch> is an ancestor of HEAD (local work sits on top)
#                                          -> branch rebuilt AT HEAD.
#   4. HEAD is an ancestor of origin/<branch> (origin moved on)
#                                          -> branch fast-forwards to origin.
#   Anything else (real divergence)       -> refuse, exit 1, touch nothing.
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "usage: tools/sync_checkout.sh <repo-dir> [branch]" >&2
  exit 1
fi

REPO="$1"
BRANCH="${2:-main}"

cd "$REPO"

git fetch origin "$BRANCH" --quiet

if git symbolic-ref -q HEAD >/dev/null; then
  echo "already on a branch ($(git symbolic-ref --short HEAD)) -- nothing to recover"
  exit 0
fi

HEAD_SHA="$(git rev-parse HEAD)"
ORIGIN_SHA="$(git rev-parse "origin/$BRANCH")"

if [ "$HEAD_SHA" = "$ORIGIN_SHA" ]; then
  git checkout -B "$BRANCH" "origin/$BRANCH" --quiet
  echo "recovered: $BRANCH now tracks origin/$BRANCH ($HEAD_SHA) -- no local-only work"
elif git merge-base --is-ancestor "$ORIGIN_SHA" "$HEAD_SHA"; then
  git checkout -B "$BRANCH" HEAD --quiet
  echo "recovered: $BRANCH rebuilt at detached HEAD ($HEAD_SHA), ahead of origin/$BRANCH ($ORIGIN_SHA) -- local work kept, nothing discarded"
elif git merge-base --is-ancestor "$HEAD_SHA" "$ORIGIN_SHA"; then
  git checkout -B "$BRANCH" "origin/$BRANCH" --quiet
  echo "recovered: $BRANCH fast-forwarded to origin/$BRANCH ($ORIGIN_SHA)"
else
  echo "refusing to touch $REPO: detached HEAD ($HEAD_SHA) has diverged from origin/$BRANCH ($ORIGIN_SHA) -- neither is an ancestor of the other. Resolve by hand." >&2
  exit 1
fi
