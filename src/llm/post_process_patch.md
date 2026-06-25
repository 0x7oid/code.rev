# DETERMINISTIC POST-PROCESSOR — CORE ENGINE SPECIFICATION (stage-agnostic)

## 0. Status and Conventions
0.1 Keywords MUST, MUST NOT, SHALL, SHALL NOT, REQUIRED, SHOULD, MAY are normative per
RFC 2119 / RFC 8174.
0.2 This document specifies a **phase-independent** post-processing engine (the **Processor**)
for any pipeline stage that emits a JSON document from a language model. The engine is
parameterized by a single value, the **StageProfile** (Section 3). No phase-specific logic
appears in the engine; all phase knowledge is supplied by the profile.

## 1. Purpose and Position
1.1 The Processor is the deterministic second step of any generation stage: a model produces a
candidate document; the Processor validates it, repairs serialization defects, normalizes
linguistic register, and either emits a canonical document or a structured failure.
1.2 The Processor corrects **form**, never **content** (1.4). Recall and analytical correctness
remain the responsibility of the generating stage.
1.3 The same engine binary serves every phase; phases differ only by their StageProfile.

## 2. Guarantees
2.1 **Determinism and purity.** With sub-stage B5 disabled (default), the Processor is a pure
function f(input, profile) -> Result, fully determined by its arguments and the pinned ruleset
and profile versions. It performs no network access and no model inference.
2.2 **Idempotence.** For any input whose Result status is 'ok' or 'ok_with_warnings',
f(Result.document, profile) MUST equal the prior Result.document.
2.3 **Form, not content.** The Processor MUST NOT add, delete, semantically reorder, or
reinterpret any value beyond the lexical normalization of Section 6. Content defects are
reported, never fabricated away.
2.4 **Fail-closed.** If validity cannot be established, the Processor MUST emit status
'unrepairable' or 'contract_failed' with document = null. No partial or guessed document is
emitted.

## 3. The StageProfile Interface (the sole parameter)
A StageProfile is a declarative record with the following members. Its authoring template and a
worked instance are given in the companion document "Stage Profile — Template and Instance".
  3.1 stageId            : string identifier of the phase (e.g. "2-structure").
  3.2 schema            : the stage's output JSON schema (for type knowledge).
  3.3 keyOrder          : ordered list of object keys per schema level, used by Stage D.
  3.4 proseFields       : path globs (Section 8.2) selecting human-prose values; the only values
                          Stage B may modify.
  3.5 evidenceFields    : path globs selecting verbatim-source values; Stage B MUST NOT touch
                          them and Stage D MUST keep them machine-safe.
  3.6 stringValueKeys   : the set of object keys whose schema type is string; consumed by the
                          Stage A field-scoped fallback (5.5).
  3.7 vocabulary        : the controlled vocabulary source for grounding (Section 6.5): a fixed
                          term set plus a rule for harvesting symbols from the document itself.
  3.8 forbiddenConcerns : a lexicon of out-of-scope terms for the phase-purity invariant (8.3
                          kind 'phase_purity').
  3.9 invariants        : an ordered list of invariant declarations (Section 8) constituting the
                          stage's Output Contract.
  3.10 lexiconExtensions: OPTIONAL stage-specific additions to the shared de-inflation maps (6.2).

## 4. Pipeline
4.1 The Processor executes four stages in fixed order:
    Stage A  JSON Validation and Repair      (Section 5)  — generic
    Stage B  Register Normalization          (Section 6)  — generic core, profile-scoped
    Stage C  Contract Validation             (Section 7)  — generic engine, profile-driven
    Stage D  Canonical Serialization         (Section 9)  — generic, profile key order
4.2 A non-recoverable error halts the pipeline and yields a failure Result (Section 10).

## 5. Stage A — JSON Validation and Repair (generic, rule-based)
5.1 **Pre-normalization (A0).** In order: strip a leading U+FEFF; normalize CRLF and CR to LF;
remove a single enclosing Markdown code fence (backticks or tildes, optional info string) if it
wraps the entire payload; trim surrounding whitespace.
5.2 **Strict parse (A1).** Attempt an RFC 8259 parse. On success, go to Stage B. On failure,
go to A2.
5.3 **Repair passes (A2).** Apply in fixed order; after each, attempt a strict parse; first
success terminates Stage A:
    R1  Quote normalization: U+201C/U+201D -> U+0022; U+2018/U+2019 -> U+0027 (before R4).
    R2  Trailing-comma removal: delete a comma followed, ignoring whitespace, by '}' or ']'.
    R3  Control-character escaping: within strings, literal LF -> backslash-n, TAB -> backslash-t.
    R4  Inner-quote escaping via the String-Membrane Scanner (5.4).
5.4 **String-Membrane Scanner (A3).** A single-pass two-state automaton (OUTSIDE, INSIDE):
    (a) OUTSIDE + U+0022 -> emit, enter INSIDE.
    (b) INSIDE + U+005C -> emit it and the next character verbatim (escape), remain INSIDE.
    (c) INSIDE + U+0022 -> look ahead past horizontal whitespace to the next significant char c:
          if c in { ',', '}', ']', ':' } or end-of-input -> TERMINATOR: emit, enter OUTSIDE;
          else -> CONTENT: emit backslash then U+0022 (escape), remain INSIDE.
    (d) any other char -> emit verbatim.
    The Scanner MUST treat a quote already preceded by an odd number of backslashes as already
    escaped and MUST NOT double-escape. Passes R1-R4 MUST each be idempotent.
5.5 **Field-scoped fallback (A4).** If A3 + parse still fails, locate value spans anchored on
each key in profile.stringValueKeys (the quoted key, colon, opening quote) and apply the Scanner
bounded to each span; re-attempt parse.
5.6 **Irrecoverable (A5).** If A4 + parse still fails, halt with the first parse-error offset, a
bounded excerpt, and the list of attempted passes.

## 6. Stage B — Register Normalization (generic core; optional model fallback)
6.1 **Scope.** Stage B operates only on values matched by profile.proseFields. It MUST NOT
modify values matched by profile.evidenceFields, any enumerated value, or any numeric value.
6.2 **B1 Lexicon substitution.** Apply the shared, versioned map M UNION profile.lexiconExtensions
by longest-match-first, case-insensitive, word-boundary-anchored replacement, preserving
sentence capitalization. M is data, pinned by Section 11.
6.3 **B2 Nominalization-to-verb.** Apply the shared, ordered regex set N once each in order;
non-matching rules leave text unchanged.
6.4 **B3 Empty-intensifier deletion.** Remove members of the shared set E except where
immediately followed by a numeral; re-collapse whitespace.
6.5 **B4 Grounding validation (report, not rewrite).** Extract candidate noun phrases by a fixed
surface heuristic (maximal TitleCase runs and multi-word lowercase compounds) and test each
against the controlled vocabulary built from profile.vocabulary (its fixed term set UNION the
symbols harvested from the document's evidence and location values per the profile rule). Each
phrase not in the vocabulary is recorded as a grounding violation { phrase, fieldPath, recordId };
it is NOT rewritten, because the correct plain term depends on the referent.
6.6 **B5 Bounded model rewrite (OPTIONAL; non-deterministic; OFF by default).** When explicitly
enabled, each grounding violation MAY be resolved by a temperature-zero single-phrase rewrite
constrained to replace only the offending phrase. B5 is excluded from 2.1 and stamped in the
Result.

## 7. Stage C — Contract Validation (generic engine, profile-driven)
7.1 The Processor evaluates each declaration in profile.invariants against the parsed tree using
the invariant-kind semantics of Section 8. Each failure is recorded as
{ invariant, kind, path, detail }.
7.2 **Repairable vs reported.** A declaration is repairable only if its kind is listed repairable
in Section 8 (machine_safe, evidence_format encoding, ordering). Repairable failures are
corrected deterministically (encoding via Stages A and D; ordering by re-sorting per the declared
keys, never altering ids). All other kinds are **content** and MUST be reported, never repaired:
the Processor MUST NOT synthesize, infer, or alter content to satisfy them.
7.3 A document with one or more unrepaired content-invariant failures yields status
'contract_failed'.

## 8. Invariant-Kind Vocabulary (the declarative checks)
8.1 Each invariant declaration is { id, kind, ...params }. The closed set of kinds:
  json_valid                                                 [structural; satisfied by Stage A]
  machine_safe(fields)            no U+0022 in matched string values          [REPAIRABLE]
  evidence_format(fields, pattern) matched values match pattern and are machine-safe [REPAIRABLE encoding]
  ordering(collection, keys)      collection sorted by the composite key list  [REPAIRABLE]
  id_format(path, regex)          every matched value matches regex            [reported]
  enum(path, domain)              every matched value is in domain (domain MAY include a regex member) [reported]
  required_nonempty(path)         every matched value is a non-empty string    [reported]
  present(path)                   the path exists and is non-empty              [reported]
  ref_integrity(from, to, nullable) every value at 'from' equals some value at 'to' (null allowed iff nullable) [reported]
  conditional(when, then)         for records matching predicate 'when', predicate 'then' holds [reported]
  count_equals(path, source)      cardinality at 'path' equals the value/size from 'source' [reported]
  set_equality(a, b)              the set selected by 'a' equals the set selected by 'b' [reported]
  coverage_grid(matrix, rows, columns) one matrix row per member of 'rows'; each row carries every member of 'columns' [reported]
  cross_consistency(left, right, match) a bijection between 'left' selections and 'right' selections under 'match' [reported]
  grounding(fields, vocabulary)   every noun phrase in matched values is grounded [reported; assisted by B4]
  phase_purity(fields, lexicon)   no matched value contains a term in 'lexicon' [reported]
8.2 **Path and glob syntax.** A selector is dot-separated keys with '[*]' for array wildcard and
'[n]' for index, e.g. 'findings[*].evidence'. A trailing '.*' selects all string leaves beneath a
node. Predicates use 'key==value' or 'key!=null'.
8.3 The engine MUST implement every kind. A profile uses only the subset it needs.

## 9. Stage D — Canonical Serialization
9.1 On success the Processor serializes with: keys in profile.keyOrder at each level; two-space
indentation; LF endings; UTF-8; every profile.evidenceFields value machine-safe.
9.2 Serialization MUST be idempotent and byte-stable for a fixed profile and ruleset version.

## 10. Result
10.1 Success:
  { "status": "ok" | "ok_with_warnings",
    "document": <canonical JSON>,
    "report": { "jsonRepairs": [...], "lexicalChanges": [...], "groundingViolations": [...],
                "contractViolations": [], "rulesetVersion": "<semver>", "profileVersion": "<semver>" } }
  'ok' when there are no warnings and no grounding violations; otherwise 'ok_with_warnings'.
10.2 Failure:
  { "status": "unrepairable" | "contract_failed",
    "document": null,
    "report": { "error": {...}, "contractViolations": [...], "attemptedRepairs": [...],
                "rulesetVersion": "<semver>", "profileVersion": "<semver>" } }
  'unrepairable' originates in Stage A (5.6); 'contract_failed' in Stage C (7.3).

## 11. Versioning and Reproducibility
11.1 The shared maps M, N, E and the engine constitute the **ruleset**, identified by a semantic
version. The StageProfile carries its own semantic version.
11.2 Every Result stamps both versions. For fixed ruleset and profile versions with B5 disabled,
f is reproducible: identical input yields byte-identical document.

## 12. Conformance
12.1 An engine is conformant if it (a) realizes Stages A-D in order, (b) preserves the guarantees
of Section 2, (c) implements every invariant kind of Section 8, (d) treats as repairable only the
kinds so designated and reports all others, and (e) contains no phase-specific logic — all phase
knowledge entering solely through the StageProfile.