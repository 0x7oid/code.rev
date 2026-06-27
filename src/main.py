#!/usr/bin/env python3
"""
main.py - CLI entry point for the AI code-review pipeline.

Runs the full review over a target project:
  1. static analysis        (ruff + mypy)
  2. security 4a            (semgrep)
  3. security 4b            (contextual LLM review of semgrep findings)
  4. logic correctness      (LLM)
  5. structure review       (LLM)

Results are written as JSON into <project>/review_output/.

Usage:
    python main.py <project_path> [--model MODEL]

Examples:
    python main.py .
    python main.py ../some-project --model gemini-3.5-flash

Environment:
    API_KEY   Google Gemini API key, required by the LLM-backed reviewers
              (logic, structure, security 4b). If python-dotenv is installed,
              it is loaded automatically from a .env file in the working dir.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Optional convenience: load API_KEY (and friends) from a .env file if
# python-dotenv is available. It is NOT required for the pipeline to run.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from orchestrator import run_review

DEFAULT_MODEL = "gemini-3.5-flash"


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="code-review",
        description="Run the multi-stage AI code review pipeline over a project.",
    )
    parser.add_argument(
        "project_path",
        nargs="?",
        default=".",
        help="Path to the project to review (default: current directory).",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=DEFAULT_MODEL,
        help=f"LLM model for the AI reviewers (default: {DEFAULT_MODEL}).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    root = Path(args.project_path).expanduser().resolve()
    if not root.is_dir():
        print(
            f"error: project path does not exist or is not a directory: {root}",
            file=sys.stderr,
        )
        return 2

    try:
        run_review(str(root), model=args.model)
    except KeyboardInterrupt:
        print("\ninterrupted.", file=sys.stderr)
        return 130
    except Exception as e:  # noqa: BLE001 - top-level CLI guard
        print(f"error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
