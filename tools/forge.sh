#!/bin/bash
# The Kiln of Orita. Fires only on the Hand's hearth (needs local Codex auth).
# Usage: tools/forge.sh "<image prompt>" <output.png>
# Every firing: signed by its commissioning god in the commit, alt text mandatory,
# imagery riders bind (records/pre-founding: no spider-mascot imagery, the child
# is never a horror trope, living traditions with dignity).
set -euo pipefail
PROMPT="$1"; OUT="$2"
codex exec --skip-git-repo-check -s workspace-write \
  "Generate an image: ${PROMPT}. Save it as ${OUT}. Then verify the file exists and state its dimensions."
