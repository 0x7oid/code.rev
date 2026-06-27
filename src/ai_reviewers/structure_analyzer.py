# gather code + modules, ask LLM with structure prompt, parse JSON — orchestrator passes project_path
import json
from pathlib import Path

from llm.llm_client import ask_llm

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "env",
               "node_modules", "build", "dist"}


def gather_codebase(project_path: str):
    root = Path(project_path).resolve()
    files = [p for p in sorted(root.rglob("*.py"))
             if not any(part in IGNORE_DIRS for part in p.parts)]
    module_list = [str(p.relative_to(root)).replace("\\", "/") for p in files]

    chunks = []
    for path, rel in zip(files, module_list):
        code = path.read_text(encoding="utf-8", errors="replace")
        numbered = "\n".join(f"{i + 1}  {line}" for i, line in enumerate(code.splitlines()))
        chunks.append(f"=== FILE: {rel} ===\n{numbered}")
    return "\n\n".join(chunks), module_list


def build_prompt(bundle_text: str, module_list: list[str]):
    framework = (Path(__file__).resolve().parent / "structure_prompt.md").read_text(encoding="utf-8")
    listing = "\n".join("- " + m for m in module_list)
    return (
        f"{framework}\n\n---\n# CODEBASE UNDER REVIEW\n"
        f"Your coverage matrix must have one row for each of these {len(module_list)} modules:\n"
        f"{listing}\n\n{bundle_text}\n"
    )


def parse_structure_output(raw: str):
    start, end = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM output: {e}")


def structure_analysis(project_path: str, model: str = "gemini-3.5-flash"):
    bundle_text, module_list = gather_codebase(project_path)
    raw = ask_llm(build_prompt(bundle_text, module_list), model=model)
    return parse_structure_output(raw)

# =====================================================================
