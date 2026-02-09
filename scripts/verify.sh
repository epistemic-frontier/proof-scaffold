#!/usr/bin/env bash
set -euo pipefail

# Dev mode ONLY: multi-repo setup with local path deps (uv sources).
# This script wires PYTHONPATH for sibling packages and runs skfd verify.
# Do NOT use this in user mode (installed packages); run `python -m skfd.cli verify <project-name>` instead.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PY="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "$VENV_PY" ]]; then
  echo "[verify.sh] .venv not found. Run: uv pip install -e .[dev]" >&2
  exit 1
fi

# Sibling repos (dev layout)
META_ROOT="$(cd "${ROOT_DIR}/.." && pwd)"
export PYTHONPATH="${META_ROOT}/metamath-prelude/src:${META_ROOT}/metamath-logic/src:${META_ROOT}/metamath-set/src"

usage() {
  echo "Usage: scripts/verify.sh <project-name>" >&2
  echo "Example: scripts/verify.sh metamath-logic" >&2
}

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

pkg="$1"

"$VENV_PY" -m skfd.cli verify "$pkg"
