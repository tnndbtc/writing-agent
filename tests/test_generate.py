"""Tests for the writing-agent generate command."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
from click.testing import CliRunner

from writing_agent.cli import main

# Path to Script.v1.json: tests/ -> repo root -> third_party/contracts/schemas/
_SCRIPT_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1] / "third_party/contracts/schemas/Script.v1.json"
)


# ---------------------------------------------------------------------------
# Test 1 — Required keys present (and no extraneous keys)
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL = {"schema_id", "genre", "project_id", "schema_version", "scenes", "script_id", "title"}
EXTRANEOUS_TOP_LEVEL = {"source_prompt_id", "generation_seed", "characters", "beats"}
REQUIRED_SCENE = {"scene_id", "location", "time_of_day", "actions"}
EXTRANEOUS_SCENE = {"beats"}


def test_required_keys(minimal_prompt, prompt_file, tmp_path):
    """All required top-level and scene keys are present; no extraneous keys exist."""
    runner = CliRunner()
    out = tmp_path / "script.json"
    result = runner.invoke(
        main, ["generate", "--prompt", str(prompt_file(minimal_prompt)), "--out", str(out)]
    )
    assert result.exit_code == 0, f"Generate failed: {result.output}"

    data = json.loads(out.read_text(encoding="utf-8"))

    missing = REQUIRED_TOP_LEVEL - data.keys()
    assert not missing, f"Missing top-level keys: {missing}"

    extra = EXTRANEOUS_TOP_LEVEL & data.keys()
    assert not extra, f"Extraneous top-level keys: {extra}"

    scene = data["scenes"][0]
    missing_scene = REQUIRED_SCENE - scene.keys()
    assert not missing_scene, f"Missing scene keys: {missing_scene}"

    extra_scene = EXTRANEOUS_SCENE & scene.keys()
    assert not extra_scene, f"Extraneous scene keys: {extra_scene}"


# ---------------------------------------------------------------------------
# Test 2 — Byte-identical across runs
# ---------------------------------------------------------------------------


def test_byte_identical_across_runs(minimal_prompt, prompt_file, tmp_path):
    """Running generate twice on the same prompt produces byte-identical output."""
    p = prompt_file(minimal_prompt)
    out1 = tmp_path / "script1.json"
    out2 = tmp_path / "script2.json"

    runner = CliRunner()

    result1 = runner.invoke(main, ["generate", "--prompt", str(p), "--out", str(out1)])
    assert result1.exit_code == 0, f"Run 1 failed: {result1.output}"

    result2 = runner.invoke(main, ["generate", "--prompt", str(p), "--out", str(out2)])
    assert result2.exit_code == 0, f"Run 2 failed: {result2.output}"

    assert out1.read_bytes() == out2.read_bytes(), "Outputs are not byte-identical"


# ---------------------------------------------------------------------------
# Test 3 — Seed variation → different output bytes
# ---------------------------------------------------------------------------


def test_seed_variation(minimal_prompt, prompt_file, tmp_path):
    """Two prompts differing only in seed produce different output bytes."""
    # seed 0 → DIALOGUE_PAIRS[0 % 3] = pair 0
    # seed 1 → DIALOGUE_PAIRS[1 % 3] = pair 1  (different lines)
    p0 = prompt_file({**minimal_prompt, "generation_seed": 0})
    p1 = prompt_file({**minimal_prompt, "generation_seed": 1})
    out0 = tmp_path / "script0.json"
    out1 = tmp_path / "script1.json"

    runner = CliRunner()

    r0 = runner.invoke(main, ["generate", "--prompt", str(p0), "--out", str(out0)])
    assert r0.exit_code == 0, f"Seed-0 run failed: {r0.output}"

    r1 = runner.invoke(main, ["generate", "--prompt", str(p1), "--out", str(out1)])
    assert r1.exit_code == 0, f"Seed-1 run failed: {r1.output}"

    assert out0.read_bytes() != out1.read_bytes(), "Different seeds should produce different output"


# ---------------------------------------------------------------------------
# Test 4 — Minimality
# ---------------------------------------------------------------------------


def test_minimality(minimal_prompt, prompt_file, tmp_path):
    """Output has exactly 1 scene with exactly 2 dialogue actions."""
    runner = CliRunner()
    out = tmp_path / "script.json"
    result = runner.invoke(
        main, ["generate", "--prompt", str(prompt_file(minimal_prompt)), "--out", str(out)]
    )
    assert result.exit_code == 0, f"Generate failed: {result.output}"

    data = json.loads(out.read_text(encoding="utf-8"))

    assert len(data["scenes"]) == 1, "Expected exactly 1 scene"

    actions = data["scenes"][0]["actions"]
    assert len(actions) == 2, "Expected exactly 2 actions"
    for action in actions:
        assert action["type"] == "dialogue", (
            f"Expected type='dialogue', got {action['type']!r}"
        )


# ---------------------------------------------------------------------------
# Test 5 — Golden output
# ---------------------------------------------------------------------------


def test_golden_output(prompt_file, tmp_path):
    """Exact field/value match against the spec's provided example.

    seed=1  →  DIALOGUE_PAIRS[1 % 3]  =  ("We're late.", "Then we move now.")
    location contains 'night'  →  time_of_day = 'night'
    """
    prompt = {
        "schema_id": "StoryPrompt",
        "schema_version": "1.0",
        "prompt_id": "prompt_0001",
        "episode_goal": "Two characters meet briefly...",
        "generation_seed": 1,
        "series": {
            "title": "Example Series",
            "genre": "Drama",
            "tone": "Contemplative",
        },
        "setting": {
            "primary_location": "Empty bus stop at night",
        },
        "characters": [
            {"id": "alex", "role": "protagonist"},
            {"id": "rin", "role": "deuteragonist"},
        ],
        "constraints": {
            "max_scenes": 1,
        },
    }

    runner = CliRunner()
    out = tmp_path / "golden.json"
    result = runner.invoke(
        main, ["generate", "--prompt", str(prompt_file(prompt)), "--out", str(out)]
    )
    assert result.exit_code == 0, f"Generate failed: {result.output}"

    data = json.loads(out.read_text(encoding="utf-8"))

    # Top-level fields
    assert data["schema_id"] == "Script"
    assert data["genre"] == "Drama"
    assert data["project_id"] == "Example Series"
    assert data["schema_version"] == "1.0.0"
    assert data["script_id"] == "prompt_0001"
    assert data["title"] == "Two characters meet briefly..."

    # Scene
    assert len(data["scenes"]) == 1
    scene = data["scenes"][0]
    assert scene["scene_id"] == "scene_1"
    assert scene["location"] == "Empty bus stop at night"
    assert scene["time_of_day"] == "night"

    # Actions — seed=1 → DIALOGUE_PAIRS[1] = ("We're late.", "Then we move now.")
    actions = scene["actions"]
    assert len(actions) == 2
    assert actions[0] == {"type": "dialogue", "speaker": "alex", "line": "We're late."}
    assert actions[1] == {"type": "dialogue", "speaker": "rin", "line": "Then we move now."}


# ---------------------------------------------------------------------------
# Invalid prompt tests (unchanged)
# ---------------------------------------------------------------------------


def _assert_invalid(runner: CliRunner, args: list[str]) -> None:
    result = runner.invoke(main, args)
    assert result.exit_code == 1, f"Expected exit code 1, got {result.exit_code}"
    assert result.stderr.strip() == "ERROR: invalid StoryPrompt", (
        f"Unexpected stderr: {result.stderr!r}"
    )


def test_invalid_prompt_wrong_schema_id(minimal_prompt, prompt_file, tmp_path):
    runner = CliRunner()
    p = prompt_file({**minimal_prompt, "schema_id": "WrongSchema"})
    _assert_invalid(runner, ["generate", "--prompt", str(p), "--out", str(tmp_path / "out.json")])


def test_invalid_prompt_empty_characters(minimal_prompt, prompt_file, tmp_path):
    runner = CliRunner()
    p = prompt_file({**minimal_prompt, "characters": []})
    _assert_invalid(runner, ["generate", "--prompt", str(p), "--out", str(tmp_path / "out.json")])


def test_invalid_prompt_missing_episode_goal(minimal_prompt, prompt_file, tmp_path):
    runner = CliRunner()
    data = {k: v for k, v in minimal_prompt.items() if k != "episode_goal"}
    p = prompt_file(data)
    _assert_invalid(runner, ["generate", "--prompt", str(p), "--out", str(tmp_path / "out.json")])


def test_invalid_prompt_malformed_json(tmp_path):
    runner = CliRunner()
    p = tmp_path / "bad.json"
    p.write_text("{ not valid json }", encoding="utf-8")
    _assert_invalid(runner, ["generate", "--prompt", str(p), "--out", str(tmp_path / "out.json")])


def test_invalid_prompt_max_scenes_zero(minimal_prompt, prompt_file, tmp_path):
    runner = CliRunner()
    data = {**minimal_prompt, "constraints": {"max_scenes": 0}}
    p = prompt_file(data)
    _assert_invalid(runner, ["generate", "--prompt", str(p), "--out", str(tmp_path / "out.json")])


# ---------------------------------------------------------------------------
# Test 11 — Output conforms to Script.v1.json contract schema
# ---------------------------------------------------------------------------


def test_output_conforms_to_schema(minimal_prompt, prompt_file, tmp_path):
    """Generated Script.json must conform to third_party/contracts/schemas/Script.v1.json."""
    runner = CliRunner()
    out = tmp_path / "script.json"
    result = runner.invoke(
        main, ["generate", "--prompt", str(prompt_file(minimal_prompt)), "--out", str(out)]
    )
    assert result.exit_code == 0, f"Generate failed: {result.output}"

    data = json.loads(out.read_text(encoding="utf-8"))
    schema = json.loads(_SCRIPT_SCHEMA_PATH.read_text(encoding="utf-8"))

    # Raises jsonschema.ValidationError if the output does not conform
    jsonschema.validate(data, schema)
