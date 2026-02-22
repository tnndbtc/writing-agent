"""Deterministic scene assembly — no I/O, no randomness, no timestamps."""

from __future__ import annotations


DIALOGUE_PAIRS = [
    ("You came.", "I said I would."),
    ("We're late.", "Then we move now."),
    ("Did anyone follow you?", "No. But we shouldn't stay."),
]


def generate_script(prompt: dict) -> dict:
    """Generate a deterministic Script dict from a validated StoryPrompt dict."""
    prompt_id        = prompt["prompt_id"]
    episode_goal     = prompt["episode_goal"]
    generation_seed  = prompt["generation_seed"]
    series           = prompt["series"]
    primary_location = prompt["setting"]["primary_location"]
    characters       = prompt["characters"]

    # time_of_day
    time_of_day = "night" if "night" in primary_location.lower() else "day"

    # deterministic dialogue via seed
    line_a, line_b = DIALOGUE_PAIRS[generation_seed % 3]
    actions = [
        {"type": "dialogue", "speaker": characters[0]["id"], "line": line_a},
        {"type": "dialogue", "speaker": characters[1]["id"], "line": line_b},
    ]

    scene = {
        "scene_id": "scene_1",
        "location": primary_location,
        "time_of_day": time_of_day,
        "actions": actions,
    }

    return {
        "genre":          series["genre"],
        "project_id":     series["title"],
        "schema_id":      "Script",
        "schema_version": "1.0.0",
        "scenes":         [scene],
        "script_id":      prompt_id,
        "title":          episode_goal,
    }
