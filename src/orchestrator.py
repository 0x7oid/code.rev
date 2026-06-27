# receives project_path, runs each analyzer, prints summaries and writes JSON results
import sys
import json
import importlib.util
from pathlib import Path

from analyzers.static_analyzer import static_analysis
from ai_reviewers.logic_correctness import logic_analysis
from ai_reviewers.structure_analyzer import structure_analysis


def load_security_module(name: str):
    path = Path(__file__).resolve().parent / "security" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_trust_model(root: Path) -> str:
    for name in ("trust_model.md", "TRUST_MODEL.md"):
        path = root / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def read_architecture_intent(root: Path) -> str | None:
    for name in ("architecture_intent.md", "ARCHITECTURE_INTENT.md"):
        path = root / name
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return None


def save_json(data, out_path: Path):
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  saved {out_path}")


def run_step(label: str, fn):
    print(f"{label}...")
    try:
        result = fn()
        print()
        return result
    except Exception as e:
        print(f"  skipped: {e}\n")
        return None


def run_review(project_path: str, model: str = "gemini-3.5-flash"):
    root = Path(project_path).resolve()
    out_dir = root / "review_output"
    out_dir.mkdir(exist_ok=True)

    print(f"Reviewing {root}\n")

    static_items = run_step("static analysis", lambda: static_analysis(str(root)))
    if static_items is not None:
        save_json(static_items, out_dir / "static_review.json")
        print(f"  {len(static_items)} issues\n")

    semgrep_result = run_step(
        "semgrep (4a)",
        lambda: load_security_module("security-a").semgrep_analysis(str(root)),
    )
    if semgrep_result is not None:
        save_json(semgrep_result, out_dir / "security_4a_review.json")
        print(f"  {len(semgrep_result.get('results', []))} findings\n")

    security_b_result = None
    if semgrep_result is not None:
        security_b = load_security_module("security-b")
        trust_model = read_trust_model(root)
        architecture_intent = read_architecture_intent(root)
        security_b_result = run_step(
            "contextual security (4b)",
            lambda: security_b.security_b_analysis(
                str(root),
                semgrep_result,
                trust_model=trust_model,
                model=model,
                architecture_intent=architecture_intent,
            ),
        )
        if security_b_result is not None:
            save_json(security_b_result, out_dir / "security_4b_review.json")
            findings = security_b_result.get("findings", [])
            print(f"  {len(findings)} contextual findings\n")

    logic_result = run_step("logic review", lambda: logic_analysis(str(root), model=model))
    if logic_result is not None:
        save_json(logic_result, out_dir / "logic_review.json")

    structure_result = run_step(
        "structure review",
        lambda: structure_analysis(str(root), model=model),
    )
    if structure_result is not None:
        save_json(structure_result, out_dir / "structure_review.json")

    print("done.")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    model = sys.argv[2] if len(sys.argv) > 2 else "gemini-3.5-flash"
    run_review(path, model=model)
