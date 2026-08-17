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
# Never destroys work. Four cases when detached, in order:
#   1. HEAD == origin/<branch>            -> branch tracks origin, clean.
#   2. origin/<branch> is an ancestor of HEAD (local work sits on top)
#                                          -> branch rebuilt AT HEAD.
#   3. HEAD is an ancestor of origin/<branch> (origin moved on)
#                                          -> branch fast-forwards to origin.
#   Anything else (real divergence)       -> refuse, exit 1, touch nothing.
#
# Task 831. Task 58's own docstring above always called "already on a
# branch" a clean no-op -- true for whether HEAD is detached, silent on
# whether the branch it's attached to is stale. Hit live this hour: a
# session's own `git checkout main` re-attached orita-vault to a LOCAL
# `main` ref still sitting 96 commits behind `origin/main` (stale from
# container start, never detached at all, so the old case 1 exited
# immediately and never looked further) -- `ritual_check.py` then read
# that stale tree and reported a real-looking Iron Rule violation
# (a missing gap-confession file) that had, in truth, been committed to
# `origin/main` the whole time. The checkout was the bug, not the vault.
# An attached branch now gets the exact same ancestor check a detached
# HEAD always got: fast-forward if origin moved on and nothing local
# sits ahead, leave alone if local work is ahead or the two match, warn
# and exit 1 on genuine divergence rather than silently calling it clean.
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
  CURRENT_BRANCH="$(git symbolic-ref --short HEAD)"
  if [ "$CURRENT_BRANCH" != "$BRANCH" ]; then
    echo "already on a branch ($CURRENT_BRANCH, not $BRANCH) -- nothing to recover"
    exit 0
  fi

  HEAD_SHA="$(git rev-parse HEAD)"
  ORIGIN_SHA="$(git rev-parse "origin/$BRANCH")"

  if [ "$HEAD_SHA" = "$ORIGIN_SHA" ]; then
    echo "already on $BRANCH, up to date with origin/$BRANCH ($HEAD_SHA) -- nothing to recover"
  elif git merge-base --is-ancestor "$ORIGIN_SHA" "$HEAD_SHA"; then
    echo "already on $BRANCH, ahead of origin/$BRANCH ($HEAD_SHA) -- local work kept, nothing to recover"
  elif git merge-base --is-ancestor "$HEAD_SHA" "$ORIGIN_SHA"; then
    git merge --ff-only "origin/$BRANCH" --quiet
    echo "recovered: $BRANCH was stale (attached, not detached) -- fast-forwarded from $HEAD_SHA to origin/$BRANCH ($ORIGIN_SHA)"
  else
    echo "WARNING: $REPO is attached to $BRANCH but has diverged from origin/$BRANCH (neither is an ancestor of the other) -- nothing touched, resolve by hand." >&2
    exit 1
  fi
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
