"""Shared pytest fixtures for writing-agent tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def minimal_prompt() -> dict:
    """A fully valid StoryPrompt dict."""
    return {
        "schema_id": "StoryPrompt",
        "schema_version": "1.0",
        "prompt_id": "ep001",
        "episode_goal": "Find the hidden treasure",
        "generation_seed": 42,
        "series": {
            "title": "Western Tales",
            "genre": "Western",
            "tone": "Adventurous",
        },
        "setting": {
            "primary_location": "Old West Town",
        },
        "characters": [
            {"id": "sheriff", "role": "protagonist"},
            {"id": "bandit", "role": "antagonist"},
        ],
        "constraints": {
            "max_scenes": 3,
        },
    }


@pytest.fixture()
def prompt_file(tmp_path: Path):
    """Factory fixture: write a dict to a uniquely-named temp JSON file, return the Path."""
    counter = {"n": 0}

    def _make(data: dict) -> Path:
        counter["n"] += 1
        p = tmp_path / f"prompt_{counter['n']}.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        return p

    return _make
