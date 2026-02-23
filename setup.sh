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
  echo "2) Show usage"
  echo "0) Exit"
  echo ""
  read -rp "Choose an option [1]: " choice
  choice="${choice:-1}"

  case "$choice" in
    1)
      echo ""
      echo "Running contract verification..."
      "$VENV/bin/python" third_party/contracts/tools/verify_contracts.py
      echo ""
      echo "Running unit tests (in-process)..."
      "$PYTEST" tests/test_generate.py -v
      echo ""
      echo "Running writing-agent generate end-to-end..."
      _ts="$(date '+%Y%m%d_%H%M%S')"
      _out="/tmp/Script_${_ts}.json"
      echo "  \$ writing-agent generate --prompt tests/examples/StoryPrompt.minimal.json --out ${_out}"
      "$VENV/bin/writing-agent" generate \
        --prompt tests/examples/StoryPrompt.minimal.json \
        --out "${_out}"
      echo "  Output: $(ls -lh "${_out}")"
      rm "${_out}"
      echo "  Removed: ${_out}"
      ;;
    2)
      echo ""
      echo "Usage:"
      echo "  writing-agent generate --prompt StoryPrompt.json --out Script.json"
      echo ""
      echo "  --prompt   Path to input StoryPrompt.json"
      echo "  --out      Path where Script.json will be written"
      echo ""
      echo "Sample StoryPrompt files are available in tests/examples/:"
      echo "  tests/examples/StoryPrompt.minimal.json   (Western, seed 42)"
      echo "  tests/examples/StoryPrompt.golden.json    (Drama, seed 1)"
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
