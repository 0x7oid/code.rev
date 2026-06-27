
# run semgrep, parse JSON, return structured results — orchestrator passes project_path
import subprocess
import json

def run_semgrep(project_path: str):
    try:
        return subprocess.run(
            [
                "semgrep",
                "--config",
                "rules/",
                "--json",
                project_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

    except FileNotFoundError:
        raise RuntimeError(
            "Semgrep is not installed or not found in PATH."
        )


def parse_semgrep_output(semgrep_output: str):
    try:
        return json.loads(semgrep_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Semgrep output: {e}")


def semgrep_analysis(project_path: str):
    result = run_semgrep(project_path)
    return parse_semgrep_output(result.stdout)

# =====================================================================
