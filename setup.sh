#!/usr/bin/env bash
set -euo pipefail

VENV="/home/tnnd/.virtualenvs/writing-agent"
PYTEST="$VENV/bin/pytest"

while true; do
  # ── Menu ────────────────────────────────────────────────────────────────────
  echo ""
  echo "writing-agent — setup menu"
  echo "---------------------------"
  echo "1) Run tests"
  echo "0) Exit"
  echo ""
  read -rp "Choose an option [1]: " choice
  choice="${choice:-1}"

  case "$choice" in
    1)
      echo ""
      echo "Running tests..."
      "$PYTEST" -v
      ;;
    0)
      echo "Bye."
      exit 0
      ;;
    *)
      echo "Unknown option: $choice" >&2
      ;;
  esac
done
