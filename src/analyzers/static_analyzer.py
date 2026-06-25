import os
import re
import json
import subprocess
from collections import defaultdict

# enable ANSI colors in Windows 10+ terminals
os.system("")


# ---------- shell ----------
def run_tool(cmd):
    """Run a command and capture stdout, stderr and the return code."""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "output_wrapper": result.stdout,
        "error_wrapper": result.stderr,
        "return_code": result.returncode,
    }


def run_static_analyzer():
    ruff_result = run_tool("ruff check . --output-format json")
    mypy_result = run_tool("mypy .")
    return ruff_result, mypy_result


# ---------- parsers ----------
def parse_ruff(ruff_output):
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
            "severity": "",            # ruff doesn't report a severity
            "message": item.get("message"),
        })
    return results


# file:line: sev: msg   AND   file:line:col: sev: msg   (+ optional trailing [code])
# non-greedy file group backtracks correctly over Windows paths (C:\...:10: ...)
_MYPY_LINE = re.compile(
    r"^(?P<file>.+?):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
    r"(?P<sev>\w+):\s*(?P<msg>.*?)(?:\s+\[(?P<code>[\w-]+)\])?$"
)


def parse_mypy(mypy_output):
    results = []
    for line in mypy_output.splitlines():
        m = _MYPY_LINE.match(line)
        if not m:
            continue  # skip summary lines like "Found 13 errors in 1 file"
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


def normalize(ruff_result, mypy_result):
    all_items = []
    all_items.extend(parse_ruff(ruff_result["output_wrapper"]))
    all_items.extend(parse_mypy(mypy_result["output_wrapper"]))
    return all_items


# ---------- pretty printer ----------
ACCENT = "\033[36m"   # single accent color (cyan) for structure
BOLD = "\033[1m"
RESET = "\033[0m"


def color(text, *codes):
    if os.environ.get("NO_COLOR") is not None:
        return text
    return "".join(codes) + text + RESET


def _int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def _short(path):
    try:
        return os.path.relpath(path)
    except Exception:
        return path or "?"


def print_cli(items):
    if not items:
        print(color("\n  No issues found\n", ACCENT, BOLD))
        return

    by_tool = defaultdict(list)
    for it in items:
        by_tool[it["tool"]].append(it)

    # ---- header ----
    parts = "   ".join(f"{t}={len(v)}" for t, v in sorted(by_tool.items()))
    print()
    print(color("=" * 64, ACCENT))
    print(color("  STATIC ANALYSIS REPORT", ACCENT, BOLD))
    print(f"  {len(items)} issues   ({parts})")
    print(color("=" * 64, ACCENT))

    for tool in sorted(by_tool):
        entries = by_tool[tool]
        print()
        print(color(f"  {tool.upper()}  ({len(entries)})", ACCENT, BOLD))
        print(color("-" * 64, ACCENT))

        by_file = defaultdict(list)
        for e in entries:
            by_file[e.get("file") or "?"].append(e)

        for f in sorted(by_file):
            print(color(f"  {_short(f)}", BOLD))
            for e in sorted(by_file[f], key=lambda x: _int(x.get("line"))):
                line = str(e.get("line", "?"))
                col = e.get("column")
                loc = f"{line}:{col}" if col else line
                sev = (e.get("severity") or "").lower()
                code = e.get("code") or ""
                print(f"    {loc.rjust(8)}  {sev.ljust(7)} {code.ljust(14)} {e.get('message', '')}")
        print()


if __name__ == "__main__":
    ruff_result, mypy_result = run_static_analyzer()
    items = normalize(ruff_result, mypy_result)
    print_cli(items)
