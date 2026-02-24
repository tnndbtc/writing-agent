"""Input validation for StoryPrompt JSON files and output validation against contracts."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema

# Paths to contract schemas relative to this file:
# src/writing_agent/ -> src/ -> repo root -> third_party/contracts/schemas/
_CONTRACTS_SCHEMAS = (
    Path(__file__).resolve().parents[2] / "third_party/contracts/schemas"
)
_STORY_PROMPT_SCHEMA_PATH = _CONTRACTS_SCHEMAS / "StoryPrompt.v1.json"
_SCRIPT_SCHEMA_PATH = _CONTRACTS_SCHEMAS / "Script.v1.json"


class ValidationError(Exception):
    """Raised when a StoryPrompt fails validation or a Script violates the contract."""


def validate_prompt_dict(data: dict) -> dict:
    """Validate an in-memory StoryPrompt dict against the contract schema and semantic rules.

    Schema-level validation (StoryPrompt.v1.json) runs first.
    Semantic rules below catch constraints that JSON Schema cannot express.

    Returns *data* unchanged on success.
    Raises ValidationError on any problem.
    """
    # 1. Schema validation against StoryPrompt.v1.json contract
    schema = json.loads(_STORY_PROMPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        raise ValidationError(f"StoryPrompt violates contract schema: {exc.message}") from exc

    # ── Semantic rules (constraints JSON Schema cannot express) ───────────────

    # 2. schema_id == "StoryPrompt"
    if data.get("schema_id") != "StoryPrompt":
        raise ValidationError("schema_id must be 'StoryPrompt'")

    # 3. schema_version, prompt_id, episode_goal are non-empty strings
    for field in ("schema_version", "prompt_id", "episode_goal"):
        v = data.get(field)
        if not isinstance(v, str) or not v.strip():
            raise ValidationError(f"'{field}' must be a non-empty string")

    # 4. generation_seed is not None
    if data.get("generation_seed") is None:
        raise ValidationError("'generation_seed' must not be None")

    # 5. series.{title,genre,tone} are non-empty strings
    series = data.get("series")
    if not isinstance(series, dict):
        raise ValidationError("'series' must be a JSON object")
    for field in ("title", "genre", "tone"):
        v = series.get(field)
        if not isinstance(v, str) or not v.strip():
            raise ValidationError(f"'series.{field}' must be a non-empty string")

    # 6. setting.primary_location is a non-empty string
    setting = data.get("setting")
    if not isinstance(setting, dict):
        raise ValidationError("'setting' must be a JSON object")
    primary_location = setting.get("primary_location")
    if not isinstance(primary_location, str) or not primary_location.strip():
        raise ValidationError("'setting.primary_location' must be a non-empty string")

    # 7. characters is a non-empty list; each item has non-empty id and role strings
    characters = data.get("characters")
    if not isinstance(characters, list) or len(characters) < 2:
        raise ValidationError("'characters' must be a list with at least 2 entries")
    for i, char in enumerate(characters):
        if not isinstance(char, dict):
            raise ValidationError(f"characters[{i}] must be a JSON object")
        for field in ("id", "role"):
            v = char.get(field)
            if not isinstance(v, str) or not v.strip():
                raise ValidationError(
                    f"characters[{i}].{field} must be a non-empty string"
                )

    # 8. constraints.max_scenes is a positive int (reject booleans)
    constraints = data.get("constraints")
    if not isinstance(constraints, dict):
        raise ValidationError("'constraints' must be a JSON object")
    max_scenes = constraints.get("max_scenes")
    if isinstance(max_scenes, bool) or not isinstance(max_scenes, int) or max_scenes <= 0:
        raise ValidationError("'constraints.max_scenes' must be a positive integer")

    return data


def validate_prompt(path: str) -> dict:
    """Read a StoryPrompt JSON file, then validate it via validate_prompt_dict.

    Returns the parsed prompt dict on success.
    Raises ValidationError on any problem.
    """
    # 1. File is readable and valid JSON
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"Cannot read file: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON: {exc}") from exc

    return validate_prompt_dict(data)


def validate_script_output(script: dict) -> None:
    """Validate a generated Script dict against the Script.v1.json contract schema.

    Raises ValidationError if the script violates the schema.
    """
    schema = json.loads(_SCRIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(script, schema)
    except jsonschema.ValidationError as exc:
        raise ValidationError(f"Script output violates contract: {exc.message}") from exc
