
# contextual security review — orchestrator passes project_path, phase_4a_findings, trust_model
import json
from pathlib import Path

from llm.llm_client import ask_llm

IGNORE_DIRS = {".git", "__pycache__", "venv", ".venv", "env",
               "node_modules", "build", "dist", "review_output"}


def is_test_module(rel: str) -> bool:
    parts = rel.replace("\\", "/").split("/")
    if "tests" in parts:
        return True
    name = Path(rel).name
    return name.startswith("test_") or name.endswith("_test.py")


def gather_module_set(project_path: str):
    root = Path(project_path).resolve()
    files = [
        p for p in sorted(root.rglob("*.py"))
        if not any(part in IGNORE_DIRS for part in p.parts)
        and not is_test_module(str(p.relative_to(root)))
    ]

    file_tree = []
    chunks = []
    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        file_tree.append(rel)
        code = path.read_text(encoding="utf-8", errors="replace")
        numbered = "\n".join(f"{i + 1}  {line}" for i, line in enumerate(code.splitlines()))
        chunks.append(f"=== FILE: {rel} ===\n{numbered}")

    return file_tree, "\n\n".join(chunks)


def normalize_phase_4a_findings(semgrep_result: dict) -> list[dict]:
    findings = []
    for i, item in enumerate(semgrep_result.get("results", []), start=1):
        rel_path = item.get("path", "")
        start_line = item.get("start", {}).get("line", 0)
        findings.append({
            "id": f"4a-{i:03d}",
            "check_id": item.get("check_id", ""),
            "message": item.get("extra", {}).get("message", item.get("message", "")),
            "location": f"{rel_path}::L{start_line}",
            "severity": item.get("extra", {}).get("severity", ""),
        })
    return findings


def build_prompt(
    file_tree: list[str],
    file_contents: str,
    phase_4a_findings,
    trust_model: str,
    architecture_intent: str | None = None,
):
    framework = (Path(__file__).resolve().parent / "security-b-prompt.md").read_text(encoding="utf-8")

    if isinstance(phase_4a_findings, dict):
        phase_4a_findings = normalize_phase_4a_findings(phase_4a_findings)

    tree_text = "\n".join(f"- {m}" for m in file_tree)
    findings_text = json.dumps(phase_4a_findings, indent=2)
    trust_text = trust_model.strip() or "(not declared — infer from code per Section 3.6a)"

    sections = [
        framework,
        "---",
        "# FILE_TREE",
        tree_text,
        "",
        "# FILE_CONTENTS",
        file_contents,
        "",
        "# PHASE_4A_FINDINGS",
        findings_text,
        "",
        "# TRUST_MODEL",
        trust_text,
    ]

    if architecture_intent:
        sections.extend(["", "# ARCHITECTURE_INTENT", architecture_intent.strip()])

    return "\n".join(sections)


def parse_security_b_output(raw: str):
    start, end = raw.find("{"), raw.rfind("}")
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse LLM output: {e}")


def security_b_analysis(
    project_path: str,
    phase_4a_findings: dict | list,
    trust_model: str = "",
    model: str = "gemini-3.5-flash",
    architecture_intent: str | None = None,
):
    file_tree, file_contents = gather_module_set(project_path)
    prompt = build_prompt(
        file_tree,
        file_contents,
        phase_4a_findings,
        trust_model,
        architecture_intent,
    )
    raw = ask_llm(prompt, model=model)
    return parse_security_b_output(raw)

# =====================================================================
