# writing-agent

A deterministic script generator that converts a **StoryPrompt** JSON document
into a **Script** JSON document.  No network calls, no randomness beyond the
seed supplied in the prompt — given the same input you always get the same
output, byte-for-byte.

---

## What it does

1. **Validates** the input `StoryPrompt.json` against the `StoryPrompt.v1.json`
   contract schema (JSON Schema + semantic rules).
2. **Generates** a `Script` — scenes, dialogue, locations — driven entirely by
   the fields in the prompt and the `generation_seed`.
3. **Validates** the generated script against the `Script.v1.json` contract
   schema before writing it to disk.
4. **Writes** the result as a byte-stable, POSIX-compliant JSON file
   (`sort_keys`, Unix line endings, single trailing newline).

---

## CLI

The package installs a single command: `writing-agent` with two sub-commands.

### Full workflow

```
story.txt  →  writing-agent compile  →  StoryPrompt.json
                                              ↓
                                    writing-agent generate  →  Script.json
```

---

### `writing-agent compile`

Parse a human-authored story text file into a validated `StoryPrompt.json`.
By default the compiled prompt is validated against canon via `world-engine`
before being written to disk.

```
writing-agent compile --story <story.txt> --out <StoryPrompt.json>
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--story` | ✅ | — | Path to story text file |
| `--out` | ✅ | — | Path where `StoryPrompt.json` will be written |
| `--world-engine-cmd` | | `world-engine` | Binary to invoke for canon validation |
| `--skip-canon` | | off | Skip canon validation (dev / standalone mode) |

**Example:**

```bash
writing-agent compile \
  --story tests/examples/StoryPrompt.minimal.story \
  --out /tmp/StoryPrompt.json
```

**Story file format** (`story.txt`):

```
# Lines starting with # and blank lines are ignored.
prompt_id:        ep001
episode_goal:     Find the hidden treasure
generation_seed:  42
series_title:     Western Tales
series_genre:     Western
series_tone:      Adventurous
primary_location: Old West Town
max_scenes:       3
character:        sheriff protagonist
character:        bandit antagonist
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Success — `StoryPrompt.json` written |
| `1` | Parse error, contract violation, or canon violation |
| `2` | `world-engine` binary not found (install it or use `--skip-canon`) |

---

### `writing-agent generate`

Generate a `Script.json` from a `StoryPrompt.json`.

```
writing-agent generate --prompt <StoryPrompt.json> --out <Script.json>
```

| Flag | Required | Description |
|------|----------|-------------|
| `--prompt` | ✅ | Path to an existing `StoryPrompt.json` input file |
| `--out`    | ✅ | Path where the generated `Script.json` will be written |

**Example:**

```bash
writing-agent generate \
  --prompt tests/examples/StoryPrompt.minimal.json \
  --out /tmp/Script.json
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Success — `Script.json` written |
| `1` | Validation failure (invalid prompt or generated script violates contract) |

---

## StoryPrompt format

```json
{
  "schema_id": "StoryPrompt",
  "schema_version": "1.0",
  "prompt_id": "ep001",
  "episode_goal": "Find the hidden treasure",
  "generation_seed": 42,
  "series": {
    "title": "Western Tales",
    "genre": "Western",
    "tone": "Adventurous"
  },
  "setting": {
    "primary_location": "Old West Town"
  },
  "characters": [
    {"id": "sheriff", "role": "protagonist"},
    {"id": "bandit",  "role": "antagonist"}
  ],
  "constraints": {
    "max_scenes": 3
  }
}
```

Sample prompts are in `tests/examples/`:

| File | Genre | Seed |
|------|-------|------|
| `StoryPrompt.minimal.json` | Western | 42 |
| `StoryPrompt.golden.json`  | Drama   | 1  |

---

## Setup

Requires Python ≥ 3.12 and an existing virtualenv at
`~/.virtualenvs/writing-agent`.  Use the interactive setup menu:

```bash
./setup.sh
```

| Option | Action |
|--------|--------|
| `1` | **Install requirements** — runs `pip install -r requirements.txt` (installs deps + the package in editable mode) |
| `2` | **Run tests** — contract verification → unit tests → end-to-end generate |
| `3` | **Show usage** — prints CLI reference |
| `0` | Exit |

---

## Project layout

```
writing-agent/
├── src/writing_agent/
│   ├── cli.py          # Click entry point (compile + generate commands)
│   ├── compiler.py     # Story text parser + world-engine gate
│   ├── generator.py    # Deterministic scene assembly
│   ├── validator.py    # StoryPrompt + Script contract validation
│   └── writer.py       # Byte-stable JSON output
├── tests/
│   ├── conftest.py
│   ├── test_compile.py
│   ├── test_generate.py
│   ├── stubs/          # world-engine stub scripts for testing
│   └── examples/       # Sample story + StoryPrompt files
├── third_party/contracts/
│   └── schemas/        # StoryPrompt.v1.json, Script.v1.json
├── requirements.txt
├── pyproject.toml
└── setup.sh
```
