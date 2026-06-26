
# first run semgrep to get the results in JSON format
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
# it shouldnt know about how to get the project path , the orchestrator should pass it as an argument , also the orchestator will carry printing out

def parse_semgrep_output(semgrep_output: str):
    try:
        return json.loads(semgrep_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Semgrep output: {e}")
    

def semgrep_analysis(project_path: str):
    result = run_semgrep(project_path)
    return parse_semgrep_output(result)

# =====================================================================








