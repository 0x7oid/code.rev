# Code.Rev

code.rev is CLI - AI-assisted code review tool for Python projects. It runs four
review phases over a target codebase, combining deterministic analysis
tools with LLM-based review. Each phase generates a separate JSON report.

Phases:

* Static Analysis
* Security
* Logic & Correctness
* Structure

Each phase targets a distinct aspect of code quality.
PS : The output can be found in test > review_output

---

# Requirements

* **Python 3.10+**
* External tools, installed via `requirements.txt`: `ruff`, `mypy`, `semgrep`.
* A **LLM API key**, set as the `API_KEY` environment variable.
  Required by phases 2b, 3, and 4 (the LLM phases). Phase 1 and the Semgrep
  stage of phase 2 do not use it.
  * By default we are using gemini-3.5-flash LLM model.
* **Internet access at run time:**
  * Phase 2a downloads Semgrep rules from the Semgrep registry on first use,
    then caches them locally (e.g. `~/.semgrep`).
  * Phases 2b, 3, and 4 call the Gemini API.

Note: Semgrep has limited native Windows support. If it cannot run, phase 2a is
skipped and the remaining phases continue.

---

# Installation

```bash
git clone https://github.com/0x7oid/code.rev.git
cd code.rev

pip install -r requirements.txt
```

Set the API key:

```bash

# macOS / Linux
export API_KEY="your_gemini_api_key"

# Windows PowerShell
$env:API_KEY = "your_gemini_api_key"
```

---

# Usage

```bash
python src/main.py <path_to_codebase> [--model MODEL]
```

Reports are written to `<path_to_codebase>/review_output/`.

Optional context files, read from the target codebase root if present:

* `trust_model.md` — used by phase 2b.
* `architecture_intent.md` — used by phase 4.

---

# Pipeline

```text
src/main.py        parse args (<path>, --model), validate, call run_review(path, model)
   │
   ▼
orchestrator.run_review(project_path, model)
   resolve path, create review_output/, run each phase via run_step() (skip-on-failure)
   ├─ static_analysis(path)                                    → static_review.json
   ├─ semgrep_analysis(path)            [security-a.py, dynamic]→ security_4a_review.json
   ├─ security_b_analysis(path, semgrep_result, trust_model,
   │                      architecture_intent, model)          → security_4b_review.json
   ├─ logic_analysis(path, model)                              → logic_review.json
   └─ structure_analysis(path, model)                          → structure_review.json
```

---

# Phase 1 — Static Analysis

Runs **Ruff** (`ruff check`) and **Mypy** (`mypy`, default configuration).

### Ruff

Detects, depending on the project's Ruff configuration:

* Undefined names
* Unused imports
* Unused variables
* Bug-prone patterns (flake8-bugbear)
* Outdated syntax that can be modernized (pyupgrade)

The exact rule set is controlled by the project's Ruff configuration
(`pyproject.toml` / `ruff.toml`).

### Mypy

Run in default mode. Detects:

* Type incompatibilities
* Invalid function signatures
* Incorrect generic usage
* Unsafe optional (`None`) handling
* Type errors across module boundaries

Default mode does not require or flag missing annotations on untyped functions.

This phase reports issues determinable without reasoning about runtime behavior.

---

# Phase 2 — Security

Two stages.

## Phase 2a — Static Security (Semgrep)

Scans the codebase with **Semgrep** using a registry ruleset (default:
`p/python`, approximately 900 rules). Rules are downloaded from the Semgrep
registry on first run and cached locally; this stage requires internet on first
use. The ruleset can be overridden with the `SEMGREP_CONFIG` environment
variable, for example:

```bash
SEMGREP_CONFIG="p/python,p/flask,p/secrets"
```

These rules match insecure **source-code patterns** (for example command
injection, code injection, and cryptographic misuse). The categories covered
depend on the selected ruleset.

This stage flags potentially dangerous patterns; it does not determine
exploitability.

Scope note: Semgrep rules analyze source code. They do **not** check
dependencies for known CVEs. Use a separate tool (e.g. `pip-audit`) for
dependency/CVE scanning.

## Phase 2b — Contextual Security (LLM)

Re-evaluates the phase 2a findings to assess whether each pattern is exploitable
in context. Uses `trust_model.md` if present. Runs only if phase 2a produced
output. Analyzes:

* Taint propagation
* Trust boundary enforcement
* Authorization integrity
* Information disclosure
* Business logic abuse
* Multi-module composition vulnerabilities

---

# Phase 3 — Logic & Correctness (LLM)

Reviews implementation correctness — defects that static analysis cannot
determine. Evaluates:

* Logical correctness
* Control flow
* State management
* Data flow consistency
* Error handling
* Edge-case handling
* Resource lifecycle
* API contract consistency
* Exception propagation
* Invariant preservation

---

# Phase 4 — Structure (LLM)

Evaluates architectural organization. Uses `architecture_intent.md` if present.
Reviews:

* Module cohesion
* Class and function responsibility
* Separation of concerns
* Dependency direction
* Circular dependencies
* Architectural layer violations
* Project and package organization
* Responsibility distribution
* Architectural consistency

# Challenges Faced
 * Making the LLM return syntaxically-correct JSON objects (not solved yet).
 * Crafting good prompts to be used in the phases that require LLM intervention (solved).

# Future Improvements
  * Running the 4 stages of the pipeline asynchronously
  * Solving the LLM-Json problem
  * Adding more stages to the pipeline , such as : Performance-Evaluation stage , to reduce time complexity and to detect known software bad codes.
