import json
import subprocess

# ok this function will be used to call a cmd command and return the output, error and return code
def run_tool(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "output_wrapper": result.stdout,
        "error_wrapper": result.stderr,
        "return_code": result.returncode
    }

def run_static_analyzer():
    ruff_result = run_tool("ruff . --output-format json")
    mypy_result = run_tool("mypy . ")
    return ruff_result, mypy_result

def parse_ruff(ruff_output):
    try:
        ruff_json = json.loads(ruff_output)
        return ruff_json
    except:
        return []
    
    results = []
    for item in ruff_json:
        results.append({
            "file" : item.get("filename"),
            "line": item.get("location", {}).get("row"),
            "code": item.get("code"),
            "message": item.get("message")
        })
    return results
def parse_mypy(mypy_output):
    results = []
    for line in mypy_output.splitlines():
        if ":" in line:
            parts = line.split(":", 3)
            if len(parts) >= 4:
                file_path = parts[0].strip()
                line_number = parts[1].strip()
                column_number = parts[2].strip()
                message = parts[3].strip()
                results.append({
                    "file": file_path,
                    "line": line_number,
                    "column": column_number,
                    "message": message
                })
    return results

def normalize(ruff_result, mypy_result):
    all_items = []

    all_items.extend(parse_ruff(ruff_result["stdout"]))
    all_items.extend(parse_mypy(mypy_result["stdout"]))

    return all_items

from collections import defaultdict
def print_cli(items):
    grouped = defaultdict(list)

    for item in items:
        grouped[item["tool"]].append(item)

    for tool, entries in grouped.items():
        print("\n" + "=" * 50)
        print(tool.upper())
        print("=" * 50)

        for e in entries:
            file = e.get("file", "?")
            line = e.get("line", "?")
            msg = e.get("message", "")

            print(f"{file}:{line} → {msg}")