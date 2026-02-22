"""CLI entry point for writing-agent."""

from __future__ import annotations

import sys

import click

from writing_agent.generator import generate_script
from writing_agent.validator import ValidationError, validate_prompt, validate_script_output
from writing_agent.writer import write_json


@click.group()
def main() -> None:
    """writing-agent — deterministic script generator."""


@main.command("generate")
@click.option(
    "--prompt",
    "prompt_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to StoryPrompt.json",
)
@click.option(
    "--out",
    "out_path",
    required=True,
    type=click.Path(),
    help="Output path for Script.json",
)
def generate(prompt_path: str, out_path: str) -> None:
    """Generate a Script.json from a StoryPrompt.json."""
    try:
        prompt = validate_prompt(prompt_path)
    except ValidationError:
        click.echo("ERROR: invalid StoryPrompt", err=True)
        sys.exit(1)

    script = generate_script(prompt)

    try:
        validate_script_output(script)
    except ValidationError:
        click.echo("ERROR: generated script violates contract", err=True)
        sys.exit(1)

    write_json(script, out_path)
    sys.exit(0)
