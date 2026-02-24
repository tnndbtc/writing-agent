"""Tests for the writing-agent compile command."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from writing_agent.cli import main

# Path helpers
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_PATH = _REPO_ROOT / "third_party/contracts/schemas/StoryPrompt.v1.json"
_STUBS_DIR   = Path(__file__).resolve().parent / "stubs"

_STUB_PASS = str(_STUBS_DIR / "world_engine_pass.sh")
_STUB_FAIL = str(_STUBS_DIR / "world_engine_fail.sh")
_STUB_MISSING = "/nonexistent/world-engine"

# ---------------------------------------------------------------------------
# Shared story text fixture
# ---------------------------------------------------------------------------

_MINIMAL_STORY = """\
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
"""


@pytest.fixture()
def story_file(tmp_path):
    """Write story text to a temp file and return its path."""
    def _make(content: str = _MINIMAL_STORY) -> Path:
        p = tmp_path / "story.txt"
        p.write_text(content, encoding="utf-8")
        return p
    return _make


# ---------------------------------------------------------------------------
# Test 1 — Valid story produces a valid StoryPrompt.json (canon skipped)
# ---------------------------------------------------------------------------

def test_compile_valid_story_skip_canon(story_file, tmp_path):
    """A well-formed story file compiles to a valid StoryPrompt.json."""
    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        [
            "compile",
            "--story", str(story_file()),
            "--out",   str(out),
            "--skip-canon",
        ],
    )
    assert result.exit_code == 0, f"compile failed: {result.output}"
    assert out.exists(), "Output file was not created"

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_id"]      == "StoryPrompt"
    assert data["prompt_id"]      == "ep001"
    assert data["episode_goal"]   == "Find the hidden treasure"
    assert data["generation_seed"] == 42
    assert data["series"]["title"]  == "Western Tales"
    assert data["series"]["genre"]  == "Western"
    assert data["series"]["tone"]   == "Adventurous"
    assert data["setting"]["primary_location"] == "Old West Town"
    assert data["constraints"]["max_scenes"]   == 3
    assert len(data["characters"]) == 2
    assert data["characters"][0] == {"id": "sheriff", "role": "protagonist"}
    assert data["characters"][1] == {"id": "bandit",  "role": "antagonist"}


# ---------------------------------------------------------------------------
# Test 2 — Output conforms to StoryPrompt.v1.json contract schema
# ---------------------------------------------------------------------------

def test_compile_output_conforms_to_schema(story_file, tmp_path):
    """Compiled StoryPrompt.json must validate against StoryPrompt.v1.json."""
    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(story_file()), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 0, f"compile failed: {result.output}"

    data   = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)  # raises if invalid


# ---------------------------------------------------------------------------
# Test 3 — Output is byte-identical across two runs (deterministic)
# ---------------------------------------------------------------------------

def test_compile_deterministic(story_file, tmp_path):
    """Compiling the same story twice produces byte-identical output."""
    runner = CliRunner()
    story = story_file()
    out1  = tmp_path / "prompt1.json"
    out2  = tmp_path / "prompt2.json"

    r1 = runner.invoke(main, ["compile", "--story", str(story), "--out", str(out1), "--skip-canon"])
    r2 = runner.invoke(main, ["compile", "--story", str(story), "--out", str(out2), "--skip-canon"])

    assert r1.exit_code == 0
    assert r2.exit_code == 0
    assert out1.read_bytes() == out2.read_bytes(), "Outputs are not byte-identical"


# ---------------------------------------------------------------------------
# Test 4 — Missing required field → exit 1
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing_field,replacement", [
    ("prompt_id:",        ""),
    ("episode_goal:",     ""),
    ("generation_seed:",  ""),
    ("series_title:",     ""),
    ("series_genre:",     ""),
    ("series_tone:",      ""),
    ("primary_location:", ""),
    ("max_scenes:",       ""),
])
def test_compile_missing_field(story_file, tmp_path, missing_field, replacement):
    """A story file missing any required field must fail with exit code 1."""
    story = _MINIMAL_STORY
    # Drop the line that contains the field key
    lines = [ln for ln in story.splitlines() if not ln.strip().startswith(missing_field.rstrip(":"))]
    broken = "\n".join(lines)

    p = tmp_path / "broken.txt"
    p.write_text(broken, encoding="utf-8")

    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(p), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 1, f"Expected exit 1 for missing {missing_field!r}"
    assert not out.exists(), "Output file must not be written on failure"


# ---------------------------------------------------------------------------
# Test 5 — Fewer than 2 characters → exit 1
# ---------------------------------------------------------------------------

def test_compile_too_few_characters(story_file, tmp_path):
    """A story with only 1 character must fail."""
    story = "\n".join(
        ln for ln in _MINIMAL_STORY.splitlines()
        if not ln.strip().startswith("character:")
    ) + "\ncharacter: sheriff protagonist\n"

    p = tmp_path / "one_char.txt"
    p.write_text(story, encoding="utf-8")

    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(p), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 1
    assert not out.exists()


# ---------------------------------------------------------------------------
# Test 6 — Non-integer generation_seed → exit 1
# ---------------------------------------------------------------------------

def test_compile_invalid_seed(story_file, tmp_path):
    """A non-integer generation_seed must fail."""
    story = _MINIMAL_STORY.replace("generation_seed:  42", "generation_seed:  notanint")
    p = tmp_path / "bad_seed.txt"
    p.write_text(story, encoding="utf-8")

    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(p), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 1
    assert not out.exists()


# ---------------------------------------------------------------------------
# Test 7 — max_scenes = 0 → exit 1
# ---------------------------------------------------------------------------

def test_compile_max_scenes_zero(story_file, tmp_path):
    """max_scenes must be a positive integer."""
    story = _MINIMAL_STORY.replace("max_scenes:       3", "max_scenes:       0")
    p = tmp_path / "zero_scenes.txt"
    p.write_text(story, encoding="utf-8")

    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(p), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 1
    assert not out.exists()


# ---------------------------------------------------------------------------
# Test 8 — world-engine not found → exit 2, no output file
# ---------------------------------------------------------------------------

def test_compile_world_engine_not_found(story_file, tmp_path):
    """When world-engine binary is missing, compile must exit 2."""
    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        [
            "compile",
            "--story",            str(story_file()),
            "--out",              str(out),
            "--world-engine-cmd", _STUB_MISSING,
        ],
    )
    assert result.exit_code == 2, f"Expected exit 2, got {result.exit_code}"
    assert not out.exists(), "Output file must not be written when world-engine is missing"


# ---------------------------------------------------------------------------
# Test 9 — world-engine returns violation → exit 1, no output file
# ---------------------------------------------------------------------------

def test_compile_world_engine_canon_violation(story_file, tmp_path):
    """When world-engine signals a canon violation, compile must exit 1."""
    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        [
            "compile",
            "--story",            str(story_file()),
            "--out",              str(out),
            "--world-engine-cmd", _STUB_FAIL,
        ],
    )
    assert result.exit_code == 1, f"Expected exit 1, got {result.exit_code}"
    assert not out.exists(), "Output file must not be written on canon violation"


# ---------------------------------------------------------------------------
# Test 10 — world-engine passes → exit 0, output file written
# ---------------------------------------------------------------------------

def test_compile_world_engine_passes(story_file, tmp_path):
    """When world-engine signals success, compile must exit 0 and write output."""
    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        [
            "compile",
            "--story",            str(story_file()),
            "--out",              str(out),
            "--world-engine-cmd", _STUB_PASS,
        ],
    )
    assert result.exit_code == 0, f"compile failed: {result.output}"
    assert out.exists(), "Output file must be written on success"

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_id"] == "StoryPrompt"


# ---------------------------------------------------------------------------
# Test 11 — --skip-canon emits warning but still succeeds
# ---------------------------------------------------------------------------

def test_compile_skip_canon_emits_warning(story_file, tmp_path):
    """--skip-canon must emit a warning and still produce output."""
    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(story_file()), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 0
    assert out.exists()
    # CliRunner mixes stderr into output; check the combined stream
    assert "WARNING" in result.output, "Expected WARNING in output"
    assert "skip-canon" in result.output.lower()


# ---------------------------------------------------------------------------
# Test 12 — Example story file round-trips cleanly
# ---------------------------------------------------------------------------

def test_compile_example_story_file(tmp_path):
    """The committed example story file compiles to a valid StoryPrompt.json."""
    example = _REPO_ROOT / "tests/examples/StoryPrompt.minimal.story"
    assert example.exists(), f"Example story file not found: {example}"

    runner = CliRunner()
    out = tmp_path / "prompt.json"
    result = runner.invoke(
        main,
        ["compile", "--story", str(example), "--out", str(out), "--skip-canon"],
    )
    assert result.exit_code == 0, f"compile failed: {result.output}"

    data   = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(data, schema)
