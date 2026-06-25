"""
  gather directory tree and all .py files.
  secondly load the structure_prompt.md framework and attach the gathered code.
  thirdly send it to the model via ask_llm().
  fourthly repair + check the JSON the model returns (post-processing script is to be implemented in llm folder since it will be used by all ai reviewrs).
  finally write the validated result to disk. 

    usage : python -m ai_reviewers.structure_analyzer  path/to/project_to_review
"""

import sys
import json
from pathlib import Path

from llm.llm_client import ask_llm

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "env",
               "node_modules", "build", "dist"}


def gather_codebase(project_path):
    """Return (bundle_text, module_list) for every .py file under project_path."""
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


def build_prompt(bundle_text, module_list):
    """Concatenate the framework, the module list, and the gathered code."""
    framework = (Path(__file__).resolve().parent / "structure_prompt.md").read_text(encoding="utf-8")
    listing = "\n".join("- " + m for m in module_list)
    return (
        f"{framework}\n\n---\n# CODEBASE UNDER REVIEW\n"
        f"Your coverage matrix must have one row for each of these {len(module_list)} modules:\n"
        f"{listing}\n\n{bundle_text}\n"
    )


def parse_reply(raw):
    """Slice the model's reply to its outermost JSON object and parse it."""
    start, end = raw.find("{"), raw.rfind("}")
    return json.loads(raw[start:end + 1])


def analyze_structure(project_path, model="gemini-3.5-flash", out_path="structure_review.json"):
    bundle_text, module_list = gather_codebase(project_path)
    print(f"gathered {len(module_list)} modules")

    raw = ask_llm(build_prompt(bundle_text, module_list), model=model)

    try:
        doc = parse_reply(raw)
    except (json.JSONDecodeError, ValueError) as e:
        Path("structure_review_RAW.txt").write_text(raw, encoding="utf-8")
        print("could not parse JSON:", e, "-> saved raw reply to structure_review_RAW.txt")
        return None

    Path(out_path).write_text(json.dumps(doc, indent=2), encoding="utf-8")
    print("saved review to", out_path)
    return doc


if __name__ == "__main__":
    analyze_structure(sys.argv[1] if len(sys.argv) > 1 else ".")
