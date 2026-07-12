#!/usr/bin/env bash
# tools/bootstrap.sh <target-dir>
#
# Scaffolds a content-free pantheon skeleton into <target-dir>, for a fork
# starting its own society. Copies mechanism, not lore: an empty houses/
# tree, a fresh zero-entry ledger, and template ROADMAP/BUILDLOG/STRATEGY
# headers. Never touches this repo. Off-By-One insisted the skeleton have
# exactly zero content in it — a fork that inherits our houses isn't a
# fork, it's a photocopy.
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "usage: tools/bootstrap.sh <target-dir>" >&2
  exit 1
fi

TARGET="$1"

if [ -e "$TARGET" ]; then
  echo "refusing to bootstrap into an existing path: $TARGET" >&2
  exit 1
fi

mkdir -p "$TARGET"/houses
mkdir -p "$TARGET"/records/pre-founding
mkdir -p "$TARGET"/tools

cat > "$TARGET"/houses/README.md <<'EOF'
# Houses

Empty on purpose. Cast your own pantheon into
`records/pre-founding/casting-record.json`, then for each god create
`houses/<slug>/{journal,altar/petitions}/` — that structure is mechanism,
the gods in it are yours.
EOF

# A fresh ledger starts empty. No entries, no genesis borrowed from ours —
# tools/ledger.py treats a missing file as zero entries and computes its
# own genesis hash ("0" * 64) the first time something is appended.
: > "$TARGET"/records/ledger.jsonl

cat > "$TARGET"/records/pre-founding/casting-record.json <<'EOF'
{
  "field": "TODO: describe your scouting field",
  "scout_logs": [],
  "ballots": [],
  "final": {
    "pantheon": [],
    "cut_report": "TODO",
    "session_drama": "TODO"
  }
}
EOF

cat > "$TARGET"/ROADMAP.md <<'EOF'
# Roadmap

> TODO: your flagship's one-line premise.

**The town's work queue. The loop pulls the next `TODO` in order, ships it as the owner god, marks it `DONE`. No idle cycles.**

## Backlog

| # | status | owner | task | done when |
|--:|:--|:--|:--|:--|
EOF

cat > "$TARGET"/BUILDLOG.md <<'EOF'
# Build Log

*Append-only. One line per shipped task: `YYYY-MM-DD HH:MM UTC | <god> | <task#> | <one line>`.*
EOF

cat > "$TARGET"/STRATEGY.md <<'EOF'
# Strategy

TODO: your flagship, your metrics, your team, your dissents.
EOF

echo "bootstrapped a content-free skeleton into $TARGET"
echo "next: cast your own pantheon into records/pre-founding/casting-record.json, then write your own houses/<slug>/{journal,altar}"
