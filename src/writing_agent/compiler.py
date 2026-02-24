"""Story text compiler — parses human-authored story files into StoryPrompt dicts."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class CompileError(Exception):
    """Raised when a story file cannot be compiled into a valid StoryPrompt."""


class CanonViolationError(Exception):
    """Raised when world-engine rejects the compiled StoryPrompt draft."""


# All scalar directive keys (order defines error messages; not parse order)
_SCALAR_FIELDS = (
    "prompt_id",
    "episode_goal",
    "generation_seed",
    "series_title",
    "series_genre",
    "series_tone",
    "primary_location",
    "max_scenes",
)


def parse_story_file(path: str) -> dict:
    """Read and parse a story text file into a raw StoryPrompt dict.

    Expected format — one directive per line; blank lines and lines starting
    with ``#`` are ignored::

        prompt_id:        <non-empty string>
        episode_goal:     <non-empty string>
        generation_seed:  <integer>
        series_title:     <non-empty string>
        series_genre:     <non-empty string>
        series_tone:      <non-empty string>
        primary_location: <non-empty string>
        max_scenes:       <positive integer>
        character:        <id> <role>
        character:        <id> <role>
        [additional character lines as needed]

    Returns a dict matching the StoryPrompt.v1.json structure.
    Raises CompileError on any parse or semantic problem.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise CompileError(f"Cannot read story file: {exc}") from exc

    fields: dict[str, str] = {}
    characters: list[dict[str, str]] = []

    for lineno, line in enumerate(raw.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if ":" not in stripped:
            raise CompileError(
                f"Line {lineno}: expected 'key: value', got: {stripped!r}"
            )

        key, _, value = stripped.partition(":")
        key = key.strip().lower()
        value = value.strip()

        if key == "character":
            parts = value.split()
            if len(parts) < 2:
                raise CompileError(
                    f"Line {lineno}: 'character' requires '<id> <role>', got: {value!r}"
                )
            characters.append({"id": parts[0], "role": " ".join(parts[1:])})

        elif key in _SCALAR_FIELDS:
            if key in fields:
                raise CompileError(f"Line {lineno}: duplicate field {key!r}")
            if not value:
                raise CompileError(f"Line {lineno}: field {key!r} must not be empty")
            fields[key] = value

        else:
            raise CompileError(f"Line {lineno}: unknown field {key!r}")

    # All scalar fields must be present
    missing = [f for f in _SCALAR_FIELDS if f not in fields]
    if missing:
        raise CompileError(f"Missing required field(s): {', '.join(missing)}")

    if len(characters) < 2:
        raise CompileError("At least 2 'character:' lines are required")

    # Integer coercions
    try:
        generation_seed = int(fields["generation_seed"])
    except ValueError:
        raise CompileError(
            f"'generation_seed' must be an integer, got: {fields['generation_seed']!r}"
        )

    try:
        max_scenes = int(fields["max_scenes"])
    except ValueError:
        raise CompileError(
            f"'max_scenes' must be an integer, got: {fields['max_scenes']!r}"
        )

    if max_scenes <= 0:
        raise CompileError(f"'max_scenes' must be a positive integer, got: {max_scenes}")

    return {
        "schema_id": "StoryPrompt",
        "schema_version": "1.0",
        "prompt_id": fields["prompt_id"],
        "episode_goal": fields["episode_goal"],
        "generation_seed": generation_seed,
        "series": {
            "title": fields["series_title"],
            "genre": fields["series_genre"],
            "tone":  fields["series_tone"],
        },
        "setting": {
            "primary_location": fields["primary_location"],
        },
        "characters": characters,
        "constraints": {
            "max_scenes": max_scenes,
        },
    }


def run_world_engine_validation(prompt_path: str, world_engine_cmd: str) -> None:
    """Invoke world-engine to validate a compiled StoryPrompt file.

    Calls::

        <world_engine_cmd> validate-story-draft --prompt <prompt_path>

    Raises:
        CompileError        — world-engine binary not found (caller should exit 2)
        CanonViolationError — world-engine rejected the prompt (caller should exit 1)
    """
    if shutil.which(world_engine_cmd) is None:
        raise CompileError(
            f"world-engine not found: {world_engine_cmd!r}\n"
            "Install world-engine or use --skip-canon to bypass canon validation."
        )

    try:
        result = subprocess.run(
            [world_engine_cmd, "validate-story-draft", "--prompt", prompt_path],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise CompileError(f"Failed to invoke world-engine: {exc}") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "(no output)"
        raise CanonViolationError(f"Canon validation failed:\n{detail}")
