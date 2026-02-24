#!/usr/bin/env bash
set -euo pipefail

VENV="/home/tnnd/.virtualenvs/writing-agent"
PYTEST="$VENV/bin/pytest"

while true; do
  # ── Menu ────────────────────────────────────────────────────────────────────
  echo ""
  echo "writing-agent — setup menu"
  echo "---------------------------"
  echo "1) Install requirements"
  echo "2) Run tests"
  echo "3) Show usage"
  echo "0) Exit"
  echo ""
  read -rp "Choose an option [1]: " choice
  choice="${choice:-1}"

  case "$choice" in
    1)
      echo ""
      echo "Installing requirements into $VENV ..."
      "$VENV/bin/pip" install -r requirements.txt
      echo ""
      echo "Done. All dependencies and the package are installed."
      ;;
    2)
      echo ""
      echo "Running contract verification..."
      "$VENV/bin/python" third_party/contracts/tools/verify_contracts.py
      echo ""
      echo "Running unit tests (in-process)..."
      "$PYTEST" tests/test_generate.py tests/test_compile.py -v
      echo ""
      echo "Running writing-agent compile + generate end-to-end..."
      _ts="$(date '+%Y%m%d_%H%M%S')"
      _prompt="/tmp/StoryPrompt_${_ts}.json"
      _out="/tmp/Script_${_ts}.json"
      echo "  \$ writing-agent compile --story tests/examples/StoryPrompt.minimal.story --out ${_prompt} --skip-canon"
      "$VENV/bin/writing-agent" compile \
        --story tests/examples/StoryPrompt.minimal.story \
        --out "${_prompt}" \
        --skip-canon
      echo "  Output: $(ls -lh "${_prompt}")"
      echo ""
      echo "  \$ writing-agent generate --prompt ${_prompt} --out ${_out}"
      "$VENV/bin/writing-agent" generate \
        --prompt "${_prompt}" \
        --out "${_out}"
      echo "  Output: $(ls -lh "${_out}")"
      rm "${_prompt}" "${_out}"
      echo "  Removed: ${_prompt} ${_out}"
      ;;
    3)
      echo ""
      echo "Usage:"
      echo ""
      echo "  Step 1 — compile a story text file into a StoryPrompt.json:"
      echo "    writing-agent compile --story story.txt --out StoryPrompt.json"
      echo ""
      echo "    --story            Path to story text file"
      echo "    --out              Path where StoryPrompt.json will be written"
      echo "    --world-engine-cmd Path/name of world-engine binary (default: world-engine)"
      echo "    --skip-canon       Skip canon validation (dev / standalone mode)"
      echo ""
      echo "  Step 2 — generate a Script.json from a StoryPrompt.json:"
      echo "    writing-agent generate --prompt StoryPrompt.json --out Script.json"
      echo ""
      echo "    --prompt   Path to input StoryPrompt.json"
      echo "    --out      Path where Script.json will be written"
      echo ""
      echo "Sample files are available in tests/examples/:"
      echo "  tests/examples/StoryPrompt.minimal.story  (story text source)"
      echo "  tests/examples/StoryPrompt.minimal.json   (compiled StoryPrompt, Western, seed 42)"
      echo "  tests/examples/StoryPrompt.golden.json    (compiled StoryPrompt, Drama, seed 1)"
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
