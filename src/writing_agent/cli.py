"""CLI entry point for writing-agent."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import click

from writing_agent.compiler import CanonViolationError, CompileError, parse_story_file, run_world_engine_validation
from writing_agent.generator import generate_script
from writing_agent.validator import ValidationError, validate_prompt, validate_prompt_dict, validate_script_output
from writing_agent.writer import write_json


@click.group()
def main() -> None:
    """writing-agent — deterministic script generator."""


@main.command("compile")
@click.option(
    "--story",
    "story_path",
    required=True,
    type=click.Path(exists=True),
    help="Path to story text file",
)
@click.option(
    "--out",
    "out_path",
    required=True,
    type=click.Path(),
    help="Output path for StoryPrompt.json",
)
@click.option(
    "--world-engine-cmd",
    default="world-engine",
    show_default=True,
    help="world-engine binary to invoke for canon validation",
)
@click.option(
    "--skip-canon",
    is_flag=True,
    default=False,
    help="Skip canon validation (standalone / dev mode)",
)
def compile_story(
    story_path: str,
    out_path: str,
    world_engine_cmd: str,
    skip_canon: bool,
) -> None:
    """Compile a story text file into a validated StoryPrompt.json.

    By default, the compiled prompt is validated against canon via world-engine
    before being written to --out.  Use --skip-canon to bypass this gate (e.g.
    during development when world-engine is not installed).
    """
    # ── 1. Parse story text → prompt dict ────────────────────────────────────
    try:
        prompt_dict = parse_story_file(story_path)
    except CompileError as exc:
        click.echo(f"ERROR: {exc}", err=True)
        sys.exit(1)

    # ── 2. Validate in-memory against StoryPrompt contract ───────────────────
    try:
        validate_prompt_dict(prompt_dict)
    except ValidationError as exc:
        click.echo(f"ERROR: compiled StoryPrompt violates contract: {exc}", err=True)
        sys.exit(1)

    # ── 3. Write to a temp file so world-engine can read it as a file ─────────
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json")
    os.close(tmp_fd)
    try:
        write_json(prompt_dict, tmp_path)

        # ── 4. Canon validation ───────────────────────────────────────────────
        if skip_canon:
            click.echo(
                "WARNING: canon validation skipped (--skip-canon)", err=True
            )
        else:
            try:
                run_world_engine_validation(tmp_path, world_engine_cmd)
            except CompileError as exc:
                click.echo(f"ERROR: {exc}", err=True)
                sys.exit(2)
            except CanonViolationError as exc:
                click.echo(f"ERROR: {exc}", err=True)
                sys.exit(1)

        # ── 5. All checks passed — move to final destination ──────────────────
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        Path(tmp_path).replace(out_path)

    finally:
        # Clean up temp file if the replace above did not already remove it
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    sys.exit(0)


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
