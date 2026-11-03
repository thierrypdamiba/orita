#!/usr/bin/env bash
# tools/env_setup.sh [repo-root]
#
# Task 2396. The other half of tools/sync_checkout.sh (task 58): that one
# recovers the checkout without re-reasoning the git judgment call by hand
# every single hour; this one rebuilds the environment without retyping
# the same five commands by hand every single hour. Every live BUILDLOG.md
# row since this town's earliest days opens with some wording of "root
# python3 lacked httpx/PyYAML/pytest/PyJWT/mypy/arcade-mcp-server,
# installed via pip ... both engine .venvs rebuilt via uv sync --extra
# dev" -- the identical five-package, two-venv litany, hand-typed fresh
# by whichever god is on duty, every cold container, for months. A
# scaffold you have to re-type by hand every hour isn't load-bearing,
# it's decoration. This script is the load-bearing version: idempotent,
# safe to run on an already-warm container (pip and uv both no-op on
# what's already satisfied), one command instead of three long ones.
#
# Root-level installs stay exactly the set every prior hour already
# typed by hand -- this script packages that known-good litany, it does
# not re-audit which of the five root packages a given tool happens to
# import today (that question is real but separate, and answering it by
# quietly dropping a package here would risk silently breaking some
# future hour's root-level `python3 -m pytest tests/...` or
# `uvx mypy --strict` invocation this script was never meant to judge).
#
# Usage: tools/env_setup.sh [repo-root]
#   repo-root: the orita checkout to operate on. Defaults to this
#     script's own repo (resolved from its own path, so it works the same
#     run from anywhere). Never touches orita-vault -- that checkout
#     carries no engine venvs and no root test suite of its own.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${1:-$(cd "${SCRIPT_DIR}/.." && pwd)}"

if [ ! -d "${ROOT}" ]; then
  echo "refusing to set up a repo root that doesn't exist: ${ROOT}" >&2
  exit 1
fi

echo "== tools/env_setup.sh: ${ROOT} =="

echo "-- root python3 deps (httpx, PyYAML, pytest, PyJWT, mypy, arcade-mcp-server) --"
python3 -m pip install --quiet --ignore-installed --break-system-packages \
  httpx PyYAML pytest PyJWT mypy arcade-mcp-server

for engine_dir in "fencepost/seam_engine" "oracle/oracle_engine"; do
  if [ -d "${ROOT}/${engine_dir}" ]; then
    echo "-- ${engine_dir} .venv (uv sync --extra dev) --"
    (cd "${ROOT}/${engine_dir}" && uv sync --extra dev --quiet)
  fi
done

echo "== env_setup.sh done: root deps present, both engine .venvs synced =="
