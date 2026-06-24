# The Process Document

This document explains the reasoning behind each step of the project.

---

## Defining the Scope

After researching with Claude, I'll stick to **Python** for these reasons:

- **Shortage of time** — Python has the lowest tooling-setup friction.
- **Easy to develop an MVP** — its static-analysis ecosystem gives me strong "ground truth" for free.

I will also limit the scope to **full-file review** (rather than diffs / PRs). This scope decision is binding on every phase below — no phase assumes a diff.

---

## Pipeline

The pipeline is composed of the following phases.

---

### Phase 1 — Static Analysis (Machine)

**Definition:** The automated, pre-execution inspection of source code as raw text, without running it. The machine parses the code into an abstract syntax tree and applies a fixed ruleset against it.

**What it examines:**

- Syntax correctness and PEP 8 compliance (`ruff`)
- Type annotation consistency and type-safety violations (`mypy`)
- Declared-but-never-used symbols: imports, variables, functions

**Input:** Raw `.py` source files.

**Output:** A structured list of violations, each with a file path, line number, rule code, and severity. No judgment, no context — just rule matches.

**Boundary:** The machine reports *what* violates a rule. It does not explain *why* it matters in this specific codebase, nor does it suggest a fix beyond the rule definition.


---

### Phase 2 — Structure (AI)

**Definition:** The inspection of how the codebase is organized at the module, class, and function level — evaluating whether the architecture reflects a coherent division of responsibility.

**What it examines:**

- **Module cohesion** — Does each file have a single, identifiable purpose? A file that handles HTTP routing, business logic, and database writes simultaneously violates cohesion.
- **Class responsibility** — Does each class own one concept? Does it expose too much state through `self`? Is it acting as a data container, a service, and a utility simultaneously?
- **Function scope** — Are functions doing one thing? A function that validates input, transforms it, writes to the database, and sends an email is four functions disguised as one.
- **Dependency direction** — Do modules at lower abstraction levels import from higher ones? That is a coupling inversion and it makes isolated testing impossible.
- **Separation of concerns** — Is business logic entangled with I/O? Are SQL queries *located* inside view handlers (an architectural placement question — not whether they are injectable)? Is configuration hardcoded inside logic?
- **Circular imports** — Do modules form import cycles that obscure the true dependency graph?

**Input:** The full module tree (full-file scope).

**Output:** A set of structural findings, each identifying a specific class or module, describing the responsibility violation, and proposing a concrete reorganization.

**Boundary:** Structure review evaluates only *where* code lives and *whether it should exist there* — never whether the logic inside it is correct (**Phase 3**), secure (**Phase 4b**), or fast (**Phase 5**). On SQL specifically, this phase only judges *placement*; injectability is **Phase 4a/4b**.

---

### Phase 3 — Logic and Correctness (AI)

**Definition:** The line-by-line reasoning pass that asks whether the code does what it is intended to do, under all possible conditions — including the ones the author did not think about.

**What it examines:**

**Control flow integrity:**

- Is every branch reachable? Is any branch **logically** unreachable given its guard conditions (dead code that requires reasoning, not the deterministic unused-symbol detection of Phase 1)?
- Do all loops have a guaranteed termination condition?
- Are `break`, `continue`, and `return` placed with clear intent, or are they patching unclear logic?

**Edge case exhaustiveness (correctness lens only):**

- What happens when a collection is empty, has one element, or has duplicate elements?
- What happens when a numeric input is zero, negative, or exceeds expected bounds — does the code *behave correctly*? (Whether that same value can be *weaponized* across a trust boundary is **Phase 4b**.)
- What happens when a string is `None`, empty, or contains special characters?
- Are default mutable arguments used? (`def fn(x=[])` creates shared state across all calls — a Python-specific correctness trap.)

**Exception handling soundness (correctness lens only):**

- Are exceptions caught at the correct abstraction level, or too early (swallowing context) or too late (letting the system crash)?
- Are bare `except:` clauses present? They intercept `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` — all of which should propagate freely.
- Is error context preserved when re-raising? (`raise e` loses the original traceback; `raise` alone preserves it.) Whether an error *leaks sensitive data to a client* is **Phase 4b**.
- Does cleanup logic execute unconditionally via `finally`, or does it depend on the happy path?

**State mutation safety (data-integrity lens only):**

- Is mutable global state being written? Every write to shared global state is a potential **data-integrity** race condition and a testing obstacle. (A race in an *authorization/permission* check — TOCTOU — is **Phase 4b**.)
- Are objects mutated in-place when the caller expects them to be unchanged? Is a defensive copy required?
- Are function arguments treated as immutable when they should be?

**Input:** Source code + the requirements or ticket that defines what the code is supposed to do. Without the requirements, correctness cannot be evaluated — only internal consistency can.

**Output:** A per-finding report identifying the file, line, the specific condition under which the logic fails, and a concrete correction.

**Boundary:** Logic review asks only one question: *does this code do what it must do, always, without exception?* It never evaluates speed (**Phase 5**), security/exploitability (**Phase 4b**), naming/style (**Phase 1/2**), or test adequacy (**Phase 6**).

---

### Phase 4a — Security: Known CVE Patterns (Machine)

**Definition:** The automated scan that matches source code against a catalog of documented, named vulnerability patterns — patterns that have a precise syntactic signature the machine can detect without understanding context.

**What it examines:**

- Use of `eval()`, `exec()`, or `compile()` on external input
- SQL query construction via string concatenation or f-strings (the injectable *signature* — not where the query is placed, which is Phase 2)
- Use of `subprocess` or `os.system` with unsanitized arguments (shell injection)
- Hardcoded credentials, tokens, or keys as string literals
- Use of deprecated or broken cryptographic primitives: MD5, SHA1, DES
- Use of `random` for security-sensitive operations instead of `secrets`
- Unsafe deserialization via `pickle.loads()` or `yaml.load()` without `Loader=SafeLoader`
- Use of `assert` statements for access control (stripped by the Python optimizer in `-O` mode)

**Tool:** `bandit`, with optional integration of `semgrep` rulesets for extended CVE coverage.

**Input:** Raw source files.

**Output:** A list of findings keyed to CVE identifiers or CWE categories where applicable, with file, line, and rule. No contextual reasoning — the machine does not know whether the `eval()` it found is reachable from an unauthenticated endpoint.

**Boundary:** This is the **only** machine-security pass in the pipeline. Phase 1 deliberately holds no security checks, so there is no duplication of `bandit`-class findings. The machine confirms the *presence* of a dangerous pattern; it cannot evaluate exploitability, reachability, or business impact — that is **Phase 4b**.

---

### Phase 4b — Contextual Security (AI)

**Definition:** The reasoning pass that evaluates security not by matching patterns, but by tracing the flow of untrusted data through the system and asking whether it can produce a harmful outcome.

**What it examines:**

- **Reachability of vulnerabilities:** A `pickle.loads()` call on line 80 is not a vulnerability if line 80 is only ever called with data read from a local config file written by the system itself. AI traces the data origin and determines whether the vulnerable pattern is actually exploitable.
- **Trust boundary violations:** Where does untrusted input enter the system (HTTP request body, query parameters, uploaded files, environment variables, inter-service messages)? Does that input reach a dangerous sink (database query, file path, subprocess call, template renderer) without being validated, sanitized, or escaped at the correct boundary?
- **Privilege and authorization logic:** Is access control enforced at the correct layer? Can a user reach a resource by bypassing the check that was only applied at the route level but not the service level? Is there a **TOCTOU** (time-of-check to time-of-use) race condition in a *permission* check? (Data-integrity races are Phase 3.)
- **Information leakage:** Are stack traces, internal paths, database schema details, or user PII included in error responses returned to the client? Are sensitive fields (passwords, tokens, session IDs) written to logs?
- **Business logic abuse (attacker-intent lens):** Can the code be used in a way that is syntactically valid but semantically harmful *by a malicious actor*? For example, can a negative quantity be passed to a purchase function to produce a credit? Can an attacker-controlled pagination limit be set arbitrarily high to **deliberately** trigger a denial-of-service? (The same heavy query degrading under *normal* load is a performance finding — **Phase 5** — and is not re-reported here.)

**Input:** Source code + the machine's findings from Phase 4a + the application's trust model (which endpoints are public, which require authentication, which handle privileged operations).

**Output:** Per-finding reports that include the full data flow path from source to sink, the condition under which the vulnerability is exploitable, and a remediation that addresses the root cause rather than just the symptom.

**Boundary:** Contextual security does not re-run pattern matching (that is Phase 4a) and does not report performance-under-normal-load (that is Phase 5). It reasons about *exploitability* only. It also independently identifies vulnerabilities that have no static signature — those that only emerge from the combination of multiple individually-safe pieces of code.

---

### Phase 5 — Performance (AI)

**Definition:** The reasoning pass that evaluates whether the code's algorithmic and architectural choices will produce acceptable runtime behavior under realistic load — without requiring the code to be executed.

**What it examines:**

- **Algorithmic complexity:** What is the time and space complexity of each function in Big-O terms? Is a linear search running on a data structure that should be a set or dictionary (O(n) → O(1))? Is a sort being called inside a loop when it could be called once outside? (This is Big-O reasoning — it never re-reports Phase 1's deterministic *cyclomatic* complexity metric.)
- **The N+1 query problem:** Is a database query, API call, or file read occurring inside a loop? Each iteration triggering a separate I/O operation is one of the most common and severe performance defects in application code. The fix is almost always batching or eager loading.
- **Unnecessary recomputation:** Is a value that does not change being recomputed on every iteration of a loop or every call to a function? This includes regex compilation (`re.compile()` outside the loop), repeated file reads, and redundant aggregations.
- **Memory allocation patterns:** Are large objects (dataframes, lists, file contents) being copied unnecessarily when they could be operated on in place? Are intermediate data structures being created and immediately discarded in a way that puts pressure on the garbage collector?
- **Blocking calls in asynchronous contexts:** In async functions, is there a synchronous blocking call — `time.sleep()`, a blocking database driver, `requests.get()` — that will stall the event loop and serialize all concurrent operations?
- **Generator vs. list tradeoffs:** Is the code materializing an entire collection into memory when a generator would process it lazily and avoid the allocation?

**Input:** Source code + knowledge of the expected data volumes and concurrency requirements (critical context — a function that is fine for 100 records may be catastrophic for 10 million).

**Output:** Per-finding reports that state the current complexity, the problematic pattern, the condition under which it becomes a bottleneck, and a concrete algorithmic or structural fix.

**Boundary:** This phase covers degradation under **normal, expected** load. A pattern that is only harmful when **deliberately abused** by an attacker is **Phase 4b**. It reasons from code alone, without execution data, and does not replace profiling — if a function is already fast enough in practice, a theoretically suboptimal algorithm is not a finding. When genuinely uncertain whether a pattern bottlenecks at scale, the correct output is a flag for profiling, not a premature optimization.

---

### Phase 6 — Test Quality (Split ownership: Machine + AI)

This phase splits cleanly into two sub-concerns owned by different actors, with no overlap:

- **Coverage measurement (Machine)** — which lines, branches, and conditions are exercised — is entirely the machine's job (`pytest-cov`). It produces an objective percentage with no interpretation required.
- **Test meaningfulness (AI)** — whether the tests that exist actually validate the right things. A test that calls a function and asserts `result is not None` covers the line but proves nothing. A mock so broad it replaces the entire module under test makes the test circular. These judgments cannot be automated.

**Boundary:** The machine reports *what fraction* of code is exercised; the AI judges *whether that exercise is meaningful*. Neither re-derives the other's output.

---

## Cross-Phase Overlap Resolution

This table is the authoritative anti-redundancy contract. Every topic that could plausibly appear in more than one phase is listed with its **single** owner per lens. A phase must **not** emit a finding outside its assigned cell.

| Topic | Appears tempting in | Strict ownership rule |
|---|---|---|
| **Security (any)** | P1 vs P4a/P4b | **P1 holds zero security checks.** Machine signatures → **P4a**. Contextual exploitability → **P4b**. Never P1. |
| **Complexity** | P1 & P5 | **P1** = cyclomatic count (deterministic maintainability metric). **P5** = algorithmic Big-O reasoning. Never both for one concern. |
| **Dead / unused code** | P1 & P3 | **P1** = deterministic unused symbols (imports/vars/funcs). **P3** = logically unreachable *branches* (requires reasoning). |
| **SQL** | P2, P4a, P4b | **P2** = *where* the query lives (placement). **P4a** = injectable string-built *signature*. **P4b** = whether untrusted data actually *reaches* it (exploitability). |
| **Race conditions** | P3 & P4b | **P3** = data-integrity races (correctness). **P4b** = TOCTOU in auth/permission (security). |
| **Input handling (None / negative / bounds)** | P3 & P4b | **P3** = does the code behave *correctly* for the value. **P4b** = can the value be *weaponized* across a trust boundary. |
| **Exceptions** | P3 & P4b | **P3** = caught at right level / context preserved (correctness). **P4b** = stack traces / PII leaking to client (information leakage). |
| **Heavy query / full-table-scan** | P4b & P5 | **P5** = degradation under *normal expected* load. **P4b** = *deliberate* DoS via attacker-controlled input. |
| **Coverage vs. test value** | P6 (internal) | **Machine** = coverage percentage. **AI** = meaningfulness of tests. Disjoint. |


- multi threading is to be used at each stage 
