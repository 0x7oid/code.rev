import re
import json
import subprocess

def run_ruff(project_path: str):
    try:
        return subprocess.run(
            ["ruff", "check", project_path, "--output-format", "json"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("Ruff is not installed or not found in PATH.")


def run_mypy(project_path: str):
    try:
        return subprocess.run(
            ["mypy", project_path],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError("Mypy is not installed or not found in PATH.")


def parse_ruff(ruff_output: str):
    try:
        ruff_json = json.loads(ruff_output)
    except (json.JSONDecodeError, TypeError):
        return []

    results = []
    for item in ruff_json:
        loc = item.get("location", {}) or {}
        results.append({
            "tool": "ruff",
            "file": item.get("filename"),
            "line": loc.get("row"),
            "column": loc.get("column"),
            "code": item.get("code"),
            "severity": "",
            "message": item.get("message"),
        })
    return results


_MYPY_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
    r"(?P<sev>\w+):\s*(?P<msg>.*?)(?:\s+\[(?P<code>[\w-]+)\])?$"
)


def parse_mypy(mypy_output: str):
    results = []
    for line in mypy_output.splitlines():
        m = _MYPY_LINE.match(line)
        if not m:
            continue
        results.append({
            "tool": "mypy",
            "file": m.group("file").strip(),
            "line": m.group("line"),
            "column": m.group("col"),
            "code": m.group("code") or "",
            "severity": m.group("sev"),
            "message": m.group("msg").strip(),
        })
    return results


def static_analysis(project_path: str):
    ruff_result = run_ruff(project_path)
    mypy_result = run_mypy(project_path)
    items = []
    items.extend(parse_ruff(ruff_result.stdout))
    items.extend(parse_mypy(mypy_result.stdout))
    return items

# =====================================================================
