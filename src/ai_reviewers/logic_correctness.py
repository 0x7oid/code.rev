# gather code + units, ask LLM with logic prompt, parse JSON — orchestrator passes project_path
import ast
import json
from pathlib import Path

from llm.llm_client import ask_llm

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "env",
               "node_modules", "build", "dist"}


def list_units(code: str, rel: str):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    return [f"{rel}::{node.name}" for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def gather_codebase(project_path: str):
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


def build_prompt(bundle_text: str, unit_list: list[str]):
    framework = (Path(__file__).resolve().parent / "logic_correctness_prompt.md").read_text(encoding="utf-8")
    listing = "\n".join("- " + u for u in unit_list)
    return (
        f"{framework}\n\n---\n# CODEBASE UNDER REVIEW\n"
        f"Your coverage matrix and probe_ledger must each have one entry for each of "
        f"these {len(unit_list)} function units:\n"
        f"{listing}\n\n{bundle_text}\n"
    )


def parse_logic_output(raw: str):
    start, end = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM output: {e}")


def logic_analysis(project_path: str, model: str = "gemini-3.5-flash"):
    bundle_text, unit_list = gather_codebase(project_path)
    raw = ask_llm(build_prompt(bundle_text, unit_list), model=model)
    return parse_logic_output(raw)

# =====================================================================
