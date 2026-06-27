# run semgrep (registry rules, downloaded on demand), parse JSON, return results
import json
import os
import subprocess

# Semgrep Registry config(s). Rules are downloaded on demand and cached in the
# user's home dir (e.g. C:/Users/<you>/.semgrep/) - NEVER stored in the project.
# NOTE: registry download REQUIRES internet at scan time.
# Override via env var (comma-separated), e.g. SEMGREP_CONFIG=p/python,p/flask
DEFAULT_CONFIG = "p/python"


def _resolve_configs():
    raw = os.environ.get("SEMGREP_CONFIG", DEFAULT_CONFIG)
    return [c.strip() for c in raw.split(",") if c.strip()]


def run_semgrep(project_path: str):
    configs = _resolve_configs()
    if not configs:
        raise RuntimeError("No semgrep config set (check SEMGREP_CONFIG).")

    cmd = ["semgrep", "scan"]
    for c in configs:
        cmd += ["--config", c]
    cmd += ["--json", project_path]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("Semgrep is not installed or not found in PATH.")

    if result.returncode >= 2:
        err = (result.stderr or "").strip() or (result.stdout or "").strip()
        if "getaddrinfo failed" in err or "Failed to resolve" in err or "Max retries" in err:
            raise RuntimeError(
                "Semgrep could not reach the rule registry (no internet?). "
                "Registry configs like 'p/python' require a network connection."
            )
        raise RuntimeError(f"Semgrep failed (exit {result.returncode}): {err[:500]}")

    return result


def parse_semgrep_output(semgrep_output: str):
    if not semgrep_output:
        raise ValueError("Semgrep produced no output to parse.")
    try:
        return json.loads(semgrep_output)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse Semgrep output: {e}")


def semgrep_analysis(project_path: str):
    result = run_semgrep(project_path)
    return parse_semgrep_output(result.stdout)
