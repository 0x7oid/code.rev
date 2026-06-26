"""
  gather directory tree and all .py files (and the list of function units to cover).
  secondly load the logic_prompt.md framework and attach the gathered code.
  thirdly send it to the model via ask_llm().
  fourthly repair + check the JSON the model returns (post-processing script is to be implemented in llm folder since it will be used by all ai reviewers).
  finally write the validated result to disk.

    usage : python -m ai_reviewers.logic_analyzer  path/to/project_to_review
"""

import sys
import ast
import json
from pathlib import Path

from llm.llm_client import ask_llm

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "env",
               "node_modules", "build", "dist"}


def list_units(code, rel):
    """Return 'rel::function' for every function/method defined in code."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [f"{rel}::{node.name}" for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def gather_codebase(project_path):
    """Return (bundle_text, unit_list) for every .py file under project_path."""
    root = Path(project_path).resolve()
    files = [p for p in sorted(root.rglob("*.py"))
             if not any(part in IGNORE_DIRS for part in p.parts)]

    chunks, unit_list = [], []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        code = path.read_text(encoding="utf-8", errors="replace")
        unit_list.extend(list_units(code, rel))
        numbered = "\n".join(f"{i + 1}  {line}" for i, line in enumerate(code.splitlines()))
        chunks.append(f"=== FILE: {rel} ===\n{numbered}")
    return "\n\n".join(chunks), unit_list


def build_prompt(bundle_text, unit_list):
    """Concatenate the framework, the unit list, and the gathered code."""
    framework = (Path(__file__).resolve().parent / "logic_prompt.md").read_text(encoding="utf-8")
    listing = "\n".join("- " + u for u in unit_list)
    return (
        f"{framework}\n\n---\n# CODEBASE UNDER REVIEW\n"
        f"Your coverage matrix and probe_ledger must each have one entry for each of "
        f"these {len(unit_list)} function units:\n"
        f"{listing}\n\n{bundle_text}\n"
    )


def parse_reply(raw):
    """Slice the model's reply to its outermost JSON object and parse it."""
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def analyze_logic(project_path, model="gemini-3.5-flash", out_path="logic_review.json"):
    bundle_text, unit_list = gather_codebase(project_path)
    print(f"gathered {len(unit_list)} units")

    raw = ask_llm(build_prompt(bundle_text, unit_list), model=model)

    try:
        doc = parse_reply(raw)
    except (json.JSONDecodeError, ValueError) as e:
        Path("logic_review_RAW.txt").write_text(raw, encoding="utf-8")
        print("could not parse JSON:", e, "-> saved raw reply to logic_review_RAW.txt")
        return None

    Path(out_path).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("saved review to", out_path)
    return doc


if __name__ == "__main__":
    analyze_logic(sys.argv[1] if len(sys.argv) > 1 else ".")
