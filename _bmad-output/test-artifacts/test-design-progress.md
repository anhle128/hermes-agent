---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-07-13'
inputDocuments:
  - '_bmad/tea/config.yaml'
  - '_bmad-output/project-context.md'
  - '_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics.md'
  - '_bmad-output/planning-artifacts/implementation-readiness-report-2026-07-12.md'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/README.md'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/workflow-provider-binding.schema.json'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/materialization-case.schema.json'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/examples/providers/archon/bindings/status-valid.json'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/examples/materialization/new-story.json'
  - 'hermes_cli/projects_db.py'
  - 'hermes_cli/sqlite_util.py'
  - 'hermes_constants.py'
  - 'hermes_cli/profiles.py'
  - 'hermes_state.py'
  - 'tests/hermes_cli/test_projects_db.py'
  - 'tests/hermes_cli/test_kanban_db_init.py'
  - 'tests/hermes_cli/test_kanban_db.py'
  - 'tests/stress/test_atypical_scenarios.py'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/risk-governance.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/probability-impact.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/test-levels-framework.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/test-priorities-matrix.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/nfr-criteria.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/playwright-cli.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/overview.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/api-request.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/auth-session.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/recurse.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/network-recorder.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/intercept-network-call.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/log.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/file-utils.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/network-error-monitor.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/fixtures-composition.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/contract-testing.md'
---

# Test Design Workflow Progress

## Step 1: Mode and Prerequisites

- **Mode:** Epic-Level
- **Reason:** The user explicitly supplied Story 2.1a as the scope. The story contains four acceptance criteria plus implementation and testing constraints, so it is a valid epic/story-level input.
- **Primary requirement artifact:** `_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md`
- **Architecture context:** Available through the story's cited architecture, PRD, epic, workflow-contract, and existing-code references, plus `_bmad-output/project-context.md`.
- **Prerequisite result:** Passed. No halt condition applies.

## Step 2: Loaded Context and Coverage Baseline

- **TEA configuration:** Playwright utils enabled; Pact.js utils disabled; Pact MCP disabled; browser automation `auto`; test stack `auto`; artifacts root `_bmad-output/test-artifacts`.
- **Detected repository stack:** Fullstack (Python backend plus multiple React/TypeScript packages). The selected story is a backend-only Python/SQLite persistence slice.
- **Browser exploration:** Not applicable and not run. Story 2.1a exposes no page, URL, API route, or graphical surface; `playwright-cli` is also not installed. Browser-level coverage would duplicate no relevant behavior.
- **Requirements loaded:** Story 2.1a ACs and task constraints, Epic 2 dependency/contract rules, FR-1 and relevant NFRs, AD-2/AD-6/AD-7/AD-8, the headless boundary, and the materialization readiness rule.
- **Contract evidence loaded:** Provider binding v1 schema, a valid Archon binding-status example, the materialization readiness schema/example, and the contract package readiness rules.
- **Prior system-level test design:** None exists under `_bmad-output`; this run must establish the story-level baseline directly from planning and code evidence.
- **Existing implementation coverage:** No `hermes_project_work` package or `tests/project_work` suite exists yet. The closest real pattern is `hermes_cli/projects_db.py` with `tmp_path` integration tests in `tests/hermes_cli/test_projects_db.py`.
- **Existing reusable test patterns:** Real SQLite connections, explicit temp DB paths, legacy-schema construction, reconnect/reopen checks, schema-structure comparisons, thread barriers, multi-process writer races, and row-count/invariant assertions.
- **Known coverage gaps:** No tests yet cover Project Binding creation/readback, stable restart identity, exact nullable JSON round-trip, all four uniqueness dimensions, aggregated conflicts, rollback/no-partial-write behavior, race fail-safe conflicts, profile-scoped uniqueness, additive/idempotent reopen, per-connect migration behavior, malformed JSON/unsupported input, connection/init failures, or contract-fixture compatibility.
- **Known reviewer evidence:** The latest readiness review records no separate 2.1a defect. The load-bearing reviewer concerns are the story's explicit warnings: do not derive binding ids, do not compare GitHub JSON text for uniqueness, collect all pre-existing conflict dimensions, preserve database constraints as a race fail-safe, never auto-suffix conflicts, keep provider identity generic, keep the explicit profile field despite per-profile files, run additive migration on every connect, use real SQLite tests, inherit materialization readiness expectations, and do not pull later validation/lifecycle/provider behavior into this story.

## Step 3: Risk and NFR Assessment

### Scoring Rules

- Probability and impact use the loaded 1–3 TEA scale; score is `P × I`.
- Score 9 is P0; scores 6–8 are P1. Per the user's rule, lower-probability issues are also promoted to P1 when they can break core behavior, security, data integrity, compatibility, or a cross-process contract.
- All risks are open until the planned automated evidence exists. Owners are roles because no individual implementation owner is named in the story.

### Risk Register

| ID | Category | Risk and evidence | P | I | Score | Priority | Mitigation / planned evidence | Owner | Timeline |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| R-01 | DATA | Blank `profile`, `display_name`, or `bound_project_cwd` can satisfy SQL `NOT NULL`; cloning `_normalize_path("")` would silently convert a blank cwd into the current process cwd and persist the wrong project identity. | 3 | 3 | 9 | P0 | Define and enforce non-blank required-field behavior before normalization; prove rejection and zero mutation. | Story 2.1a developer + product owner | Before implementation/merge |
| R-02 | DATA | Profile-scoped uniqueness can be bypassed by path spelling differences, incorrect partial-index predicates, or global instead of per-profile constraints. Optional `NULL` values must not collide. | 3 | 3 | 9 | P0 | Use normalized stored keys plus four persistence constraints; test each dimension independently, profile isolation, nullable boundaries, and equivalent path spellings. | Story 2.1a developer + test architect | Before merge |
| R-03 | DATA | The GitHub reference input contract is not defined beyond an example such as lowercased `owner/repo`; key names, accepted shapes, blank components, and case behavior are UNKNOWN. JSON text equality would miss semantic duplicates. | 3 | 3 | 9 | P0 | Clarify the minimal structured input contract; derive one canonical key from semantic owner/repo values; reject malformed/partial values without mutation. | Product owner + architect | Before coding the key function |
| R-04 | TECH | Provider metadata is contract-sensitive, but behavior for metadata without both generic `provider` and `name`, a partial tuple, or disagreement between indexed columns and the opaque blob is unspecified. | 3 | 3 | 9 | P0 | Treat structural provider/name presence and agreement as a persistence-boundary contract; load the real v1 fixture, reject partial/inconsistent shapes, and preserve the remaining metadata exactly. | Architect + Story 2.1a developer | Before implementation/merge |
| R-05 | DATA | A create can collide on multiple dimensions. Returning only SQLite's first constraint, auto-suffixing, retrying, or mutating before returning would violate AC2 and hide ambiguity. | 2 | 3 | 6 | P1 | Pre-check every dimension inside one IMMEDIATE transaction; return all dimension→existing-id mappings; assert row count and prior row are unchanged; repeated create remains a conflict. | Story 2.1a developer | Before merge |
| R-06 | DATA | Two processes can pass an application pre-check concurrently unless `BEGIN IMMEDIATE` and database constraints serialize/fail closed. An `IntegrityError` must not escape or create two rows. | 2 | 3 | 6 | P1 | Run a real two-writer race against one DB; prove exactly one row, one success, and one structured conflict. Keep unique indexes as the final authority. | Story 2.1a developer + test architect | Before merge; burn-in in CI |
| R-07 | DATA | Stable identity or exact field fidelity can be lost across close/reopen if ids are derived/recomputed, nullable fields drift, or JSON is not parsed back to the public dataclass shape. | 2 | 3 | 6 | P1 | Generate once, close, open a new connection, and compare every persisted/public field plus `to_dict()`; prove id remains unchanged. | Story 2.1a developer | Before merge |
| R-08 | TECH | Schema initialization can skip additive migration because of `_INITIALIZED_PATHS`, race on first connect, or fail after reopen. The story explicitly requires migration on every `connect()`, unlike the closest analog's current placement inside its cache guard. | 2 | 3 | 6 | P1 | Test fresh, repeated, legacy-shaped, cached-path, and concurrent connects; spy only on migration call count while validating schema/data with real SQLite. | Story 2.1a developer | Before merge |
| R-09 | OPS / SEC | The DB is per-profile but `HERMES_HOME` fallback can route a process to the default DB. Omitting or misresolving the explicit profile column makes cross-profile writes indistinguishable and can leak project context across profiles. | 2 | 3 | 6 | P1 | Test profile-aware path resolution with temp homes, explicit self-describing rows, same keys allowed in distinct profiles/DBs, and profile-filtered lookup. | Story 2.1a developer + security reviewer | Before merge |
| R-10 | TECH / DATA | Non-dict, non-serializable, non-standard JSON (`NaN`/Infinity), or corrupted JSON can fail mid-create or break reads after restart. Misclassifying such failures as uniqueness conflicts would corrupt the machine contract. | 2 | 3 | 6 | P1 | Define strict JSON inputs (`allow_nan=False` or equivalent), reject malformed input before write, distinguish non-unique failures, and verify rollback; document corrupt-on-disk read behavior. | Story 2.1a developer | Before merge |
| R-11 | DATA | The random id can theoretically collide. A primary-key `IntegrityError` must never overwrite a binding or be falsely attributed to a business uniqueness dimension. | 1 | 3 | 3 | P1 (domain promotion) | Inject a deterministic id collision; prove no overwrite and return a structured internal-id conflict or bounded regeneration policy chosen by the owner. | Story 2.1a developer | Before merge |
| R-12 | TECH / DATA | `abspath + expanduser + strip` does not collapse symlink aliases and may not case-fold Windows paths, allowing two physical-project aliases to evade textual uniqueness. Cross-platform expectations are UNKNOWN. | 2 | 3 | 6 | P1 | Clarify textual-path versus physical-path identity. Cover documented normalization on all platforms and add a Windows/case or symlink waiver if physical equivalence remains Story 2.1b work. | Architect + product owner | Before merge decision |
| R-13 | TECH | Mock-only tests or tests that duplicate mutable schema values can pass while transaction, migration, row factory, WAL fallback, and contract-fixture behavior is broken. | 2 | 3 | 6 | P1 | Use real imports and temp SQLite files; assert behavior/invariants; load real contract examples; run through the project's isolated test runner. | Test architect + Story 2.1a developer | Before merge |
| R-14 | OPS / DATA | DB-open, WAL setup, lock contention, or insert failure can leave a transaction open, mask the original error, or partially mutate state. | 2 | 2 | 4 | P1 (core-behavior promotion) | Exercise injected dependency/insert failure around a real connection; assert rollback, unchanged count, usable follow-up connection, and original error semantics. Reuse existing WAL-helper tests instead of duplicating them. | Story 2.1a developer | Before merge |
| R-15 | PERF / OPS | No latency, binding-count, busy-timeout, or concurrent-writer threshold is specified. Performance/scalability targets are UNKNOWN. | 1 | 2 | 2 | P2 | Record the gap; use a small concurrency burn-in as reliability evidence, not an invented SLO. Add performance tests only if a product threshold or production contention appears. | Product owner + operations | Follow-up trigger only |

### Reviewer Concern Disposition

| Concern | Evidence classification | Linked item and rationale |
| --- | --- | --- |
| Persist a random stable id; do not derive it from cwd/artifacts. | Risk | R-07. Derivation changes identity semantics and can break every downstream reference. |
| Do not use JSON serialization equality for GitHub uniqueness. | Risk | R-03. Object key order/case can bypass semantic uniqueness. |
| Collect every collided uniqueness dimension and existing id. | Risk | R-05. First-error-only diagnostics violate AC2's plural contract. |
| Keep DB unique constraints as the concurrency fail-safe. | Risk | R-06. Application pre-checks alone are not race-safe. |
| Reject ambiguous creates; never auto-suffix/dedupe. | Risk | R-05. Auto-suffixing turns a required conflict into silent mutation. |
| Use partial unique indexes so optional `NULL` fields do not collide. | Risk | R-02. Incorrect predicates break optional-field behavior and uniqueness. |
| Keep `profile` on the row even though the file is per-profile. | Risk | R-09. It is diagnostic evidence for wrong-home routing and profile-scoped queries. |
| Use generic provider/name Controller Identity and preserve opaque metadata. | Risk | R-04. Provider-specific or inconsistent fields break the shared contract. |
| Run additive migration on every connect; initialization remains idempotent. | Risk | R-08. The cache must not suppress future additive migration work. |
| Use real SQLite/tmp-path tests, not only mocks. | Risk | R-13. Transaction and reopen behavior cannot be proven with mocks. |
| Carry migration, uniqueness, and idempotency expectations from materialization fixtures. | Risk | R-13, R-08, R-02, and R-06. The readiness rule is test evidence, not optional documentation. |
| Clone the per-profile Projects-store shape, not the shared Kanban ownership model. | Risk | R-09 and R-13. The wrong analog changes data ownership and profile isolation. |
| Do not create the full architecture seed or wire commands/tools in this story. | Explicit non-risk | NR-08. The change is intentionally additive and storage-only; extra modules/surfaces would be scope creep. |
| Defer cwd safety, lifecycle/status, provider lifecycle/health, and BMAD mounting. | Explicit non-risk | NR-02 through NR-05. Those behaviors have named later-story owners and are not silently omitted. |
| External Archon runtime output is absent. | Explicit non-risk | NR-07. Story 2.1a stores opaque metadata and can validate local fixture compatibility without calling/consuming an Archon runtime result. |
| AC1 says “authorized command,” while the task adds no command surface. | Explicit non-risk with follow-up | NR-01. There is no externally callable surface in this story; authorization must be tested when a command/API invokes this repository. |

### Explicit Non-Risks and Deferred Boundaries

| ID | Current P | Current I | Score | Rationale / current owner | Residual trigger |
| --- | ---: | ---: | ---: | --- | --- |
| NR-01 | 1 | 3 | 3 | Authorization is not enforceable in an internal persistence repository with no command/API surface. Owner: first story that exposes create/read. | Re-score as SEC P0/P1 when a command, API, tool, or agent action calls `create_binding()`. |
| NR-02 | 1 | 3 | 3 | Cwd existence, allowed roots, and git-repo safety are explicitly Story 2.1b. Story 2.1a must not enable actions. | Re-score if any workflow action can consume an unvalidated binding. |
| NR-03 | 1 | 2 | 2 | Update, disable, repair, re-enable, validation state, and audit history belong to Story 2.1c. | Re-score when mutable lifecycle operations are added. |
| NR-04 | 1 | 3 | 3 | Provider registration, refresh, health, rotation, and conflict diagnosis belong to Story 3.2; 2.1a only stores structurally compatible opaque metadata. | Re-score when provider I/O or status interpretation is introduced. |
| NR-05 | 1 | 2 | 2 | BMAD skill mounting and `skills.external_dirs` mutation belong to Story 2.2. | Re-score when stored `bmad_skill_dir` starts driving mount behavior. |
| NR-06 | 1 | 1 | 1 | Out-of-order/stale events, cancellation, and external timeouts are not part of a synchronous single-row SQLite create/read repository. | Re-score if asynchronous commands, retries, queues, or events are added. |
| NR-07 | 1 | 2 | 2 | External Archon producer evidence is not consumed by this local opaque-storage story. Local schema/example compatibility is available. | Re-score when Hermes parses provider results or asserts provider runtime compatibility. |
| NR-08 | 1 | 2 | 2 | UI/browser/E2E and full architecture-seed coverage have no surface in Story 2.1a. | Re-score when a user-facing command/UI or additional project-work modules are introduced. |

### NFR Planning

| NFR area | In-scope planning status | Measurable planned evidence / unknowns |
| --- | --- | --- |
| Security / authorization | Deferred surface, but profile isolation is in scope. | No external create/read surface may be introduced; distinct temp profile homes must not share rows; row profile remains explicit. Authorization evidence is triggered by the first public caller. |
| Reliability / data integrity | In scope and release-critical. | After restart every field/id matches; conflicts and injected failures leave the row count unchanged; concurrent same-key creates persist exactly one row; repeated schema open preserves data. |
| Compatibility / migration | In scope and release-critical. | Fresh and existing-schema opens succeed; schema objects are not duplicated; additive migration is invoked on every connection; real provider fixture data round-trips without vocabulary drift. |
| Maintainability | In scope. | Tests use behavior contracts, real SQLite, explicit temp paths, and the existing small-store helpers; no schema-count or config-version snapshots. |
| Performance / scalability | UNKNOWN. | No latency, data-volume, or writer-count requirement exists. Do not invent an SLO; use only bounded concurrency burn-in for race evidence. |
| Compliance | Not specified. | No compliance requirement or threshold appears in the story/PRD slice. |

### Highest-Risk Summary

The immediate design blockers are R-01 through R-04. The required-field contract, GitHub canonical input shape, and provider structural identity must be made deterministic before tests or implementation can be authoritative. R-05 through R-14 then require P1 evidence at the real SQLite boundary; none may be left implicit behind a happy-path restart test.

## Step 4: Coverage Plan and Execution Strategy

### Test-Level Strategy

- **Integration (primary):** `pytest` with real SQLite files under `tmp_path`, real module imports, new connections for restart, and real threads/processes for races. This is the project's correct level for persistence, migration, profile routing, and transaction behavior.
- **Unit (selective):** pure path/GitHub-key/id helpers only, where a database would add no signal.
- **Contract validation:** the existing Workflow Commander validator plus a real fixture round-trip through Project Binding storage.
- **No API/E2E/UI layer:** Story 2.1a deliberately introduces no command, route, tool, or UI surface. Waiver W-01/W-08 records the ownership trigger.

### Atomic Scenario Catalog

#### Core Create/Read and Input Boundaries

| ID | Pri | Level | Atomic scenario | Trace |
| --- | --- | --- | --- | --- |
| 2.1A-INT-001 | P1 | Integration | Create one binding on a fresh DB with every required/optional field; assert one row, returned stable id, normalized stored paths, and machine-readable success. | AC1, R-01, R-07 |
| 2.1A-INT-002 | P1 | Integration | Close the creating connection, open a new connection to the same file, read by id, and compare every dataclass/`to_dict()` field and the unchanged id. | AC1, AC3, R-07 |
| 2.1A-INT-003 | P1 | Integration | Read a syntactically valid but unknown binding id; return `None` with no mutation. | AC3 |
| 2.1A-INT-004 | P1 | Integration | List bindings for one profile; return only rows for that profile and every public persisted field, comparing as a set rather than freezing order. | AC3, R-09 |
| 2.1A-INT-005 | P1 | Integration | Reject blank/whitespace profile before SQL and leave row count zero. | R-01 |
| 2.1A-INT-006 | P1 | Integration | Reject blank/whitespace display name before SQL and leave row count zero. | R-01 |
| 2.1A-INT-007 | P0 | Integration | Reject blank/whitespace cwd before path normalization so it cannot become the process cwd; leave row count zero. | R-01 |
| 2.1A-INT-008 | P1 | Integration | Parameterized `None`/unsupported-type required fields fail deterministically before mutation and are not reported as uniqueness conflicts. | R-01, R-10 |
| 2.1A-INT-009 | P1 | Integration | Create two otherwise distinct bindings with all optional references `NULL`; both persist, proving partial indexes do not make `NULL` values collide. | AC1, R-02 |
| 2.1A-INT-010 | P1 | Integration | Cwd spellings that normalize to the same absolute path (`..`, trailing separator, relative form) collide within one profile. | AC2, R-02 |
| 2.1A-INT-011 | P1 | Integration | BMAD skill directory spellings that normalize to the same absolute path (`~`, `..`, trailing separator) collide within one profile. | AC2, R-02 |
| 2.1A-INT-012 | P1 | Integration | Filesystem-root input remains root after trailing-separator stripping and is not normalized to an empty string. | R-02, R-12 |
| 2.1A-INT-013 | P0 | Integration | Semantically equal GitHub references with different key order and owner/repo case collide on one canonical key. | AC2, R-03 |
| 2.1A-INT-014 | P1 | Integration | Parameterized non-mapping, missing owner, missing repo, and blank-component GitHub references are rejected with zero mutation. | R-03, R-10 |
| 2.1A-INT-015 | P1 | Integration | A valid GitHub reference round-trips exactly as supplied while its separate canonical key drives uniqueness. | AC3, R-03 |
| 2.1A-INT-016 | P1 | Contract integration | Load `status-valid.json`, persist generic `provider`/`name` and the remaining binding metadata, restart, and compare the opaque metadata exactly. | AC1, AC3, R-04, R-13 |
| 2.1A-INT-017 | P0 | Integration | Parameterized provider metadata with only provider, only name, missing tuple, blank tuple member, or tuple/blob disagreement is rejected without mutation. | R-04, R-10 |
| 2.1A-INT-018 | P1 | Integration | Bindings with different complete provider/name tuples in one profile are both allowed, proving tuple—not provider alone—is the identity. | R-04 |

#### Uniqueness, Duplicate Actions, and Races

| ID | Pri | Level | Atomic scenario | Trace |
| --- | --- | --- | --- | --- |
| 2.1A-INT-019 | P0 | Integration | Parameterize each of the four uniqueness dimensions; each duplicate returns `conflict=true`, the exact dimension and existing id, no escaping `IntegrityError`, and row count one. | AC2, R-02, R-05 |
| 2.1A-INT-020 | P1 | Integration | Seed separate existing rows so one candidate collides on all four dimensions; return all dimension→id entries and persist no candidate row. | AC2, R-05 |
| 2.1A-INT-021 | P1 | Integration | Repeat the exact create action; reject as a conflict with the original id, do not auto-suffix/retry, and keep one row. | AC2, R-05; duplicate action regression |
| 2.1A-INT-022 | P1 | Integration | The same cwd/GitHub/BMAD/provider identity values under a different profile are allowed in one DB; uniqueness is not global. | AC2, R-02, R-09 |
| 2.1A-INT-023 | P1 | Integration | Force the pre-check to miss while the real unique index rejects the insert; the `IntegrityError` fail-safe returns a structured conflict and does not leak/duplicate. | AC2, R-06 |
| 2.1A-INT-024 | P1 | Cross-process integration | Two spawned processes concurrently create the same binding identity; exactly one succeeds, one returns structured conflict, both exit cleanly, and the DB has one row. | AC2, R-06 |
| 2.1A-INT-025 | P1 | Cross-process integration | Two spawned processes concurrently create distinct identities; both succeed and both rows remain readable after reopen. | R-06, R-14 |

#### Profile Routing, Restart, and Schema Lifecycle

| ID | Pri | Level | Atomic scenario | Trace |
| --- | --- | --- | --- | --- |
| 2.1A-INT-026 | P1 | Integration | Mixed-profile rows in one explicit test DB are filtered correctly by `list_bindings_for_profile`. | AC3, R-09 |
| 2.1A-INT-027 | P1 | Integration | With context-local/temp Hermes homes for two profiles, `project_bindings_db_path()` resolves to each profile's own `project_bindings.db`. | R-09 |
| 2.1A-INT-028 | P1 | Integration | Active profile resolution stores the real profile; a resolver exception stores documented fallback `default`, keeping the row self-describing. | AC1, R-09 |
| 2.1A-INT-029 | P1 | Integration | Create in profile-home A and read from profile-home B; B cannot see A's row, while A can after reopen. | AC1, R-09 |
| 2.1A-INT-030 | P1 | Integration | Reopen a current-schema DB twice without clearing data; no table/column/index error occurs and the original binding remains unchanged. | AC4, R-08 |
| 2.1A-INT-031 | P1 | Integration | Instrument only the migration seam while using a real DB; verify it is called on every `connect()`, including when schema initialization is cached. | AC4, R-08 |
| 2.1A-INT-032 | P1 | Integration | Clear `_INITIALIZED_PATHS` to simulate a new process, reopen the same DB, and prove schema/data remain valid. | AC4, R-08 |
| 2.1A-INT-033 | P1 | Threaded integration | Release multiple threads into first `connect()` for one new path; all close cleanly and one usable schema results. | AC4, R-08 |
| 2.1A-INT-034 | P1 | Integration | Delete/recreate a DB file after its path is cached, then reconnect; schema must be recreated or the cache invalidated rather than producing `no such table`. | R-08; stale-cache regression |
| 2.1A-INT-035 | P1 | Integration | Inspect `PRAGMA table_info/index_list/index_info` for required column relationships and four unique behaviors/predicates without snapshotting mutable object counts or names unnecessarily. | AC4, R-02, R-08 |
| 2.1A-INT-036 | P2 | Integration | Exit `connect_closing()` and prove the connection is closed, preventing per-operation file-descriptor accumulation. | Maintainability |

#### JSON, Identity, Failure, Rollback, and Dependency Behavior

| ID | Pri | Level | Atomic scenario | Trace |
| --- | --- | --- | --- | --- |
| 2.1A-INT-037 | P1 | Integration | Nested Unicode, booleans, arrays, and JSON `null` in GitHub/provider metadata survive a close/reopen exact round-trip. | AC3, R-07, R-10 |
| 2.1A-INT-038 | P1 | Integration | Non-serializable objects and non-standard constants (`NaN`, ±Infinity) are rejected before insert; row count remains zero. | R-10 |
| 2.1A-INT-039 | P1 | Integration | Corrupt a stored JSON blob directly, then read; fail explicitly as data corruption rather than silently dropping/substituting metadata. | R-10 |
| 2.1A-INT-040 | P1 | Integration | Create/restart with changed input-variable ordering/path objects and prove the stored id is not recomputed from mutable field values. | AC1, R-07 |
| 2.1A-INT-041 | P1 | Integration | Inject a repeated id for two business-distinct creates; preserve the first row and return/regenerate per the clarified internal-id collision contract, never mislabeling a business dimension. | R-11 |
| 2.1A-INT-042 | P1 | Integration | Inject an `OperationalError` at insert inside a real IMMEDIATE transaction; the original error propagates, row count is unchanged, and a later create on the connection succeeds. | AC2, R-05, R-10, R-14; partial failure/rollback |
| 2.1A-INT-043 | P1 | Integration | Hold an IMMEDIATE transaction on connection A, set a bounded busy timeout on B, and attempt create; B times out with no row, then succeeds after A releases. | R-14; timeout/rollback |
| 2.1A-INT-044 | P1 | Integration | Use a DB parent path that is a regular file; connection fails without creating/marking an initialized DB, and a later valid path connects successfully. | R-14; dependency/permission-path failure |
| 2.1A-INT-045 | P1 | Integration | A real connected DB has foreign keys enabled and an actual journal mode of WAL or documented DELETE fallback, proving Project Binding wiring without retesting the helper's full internals. | R-13, R-14 |
| 2.1A-VAL-001 | P1 | Contract validation | Run the shipped Workflow Commander validator; it must pass before the fixture-based Project Binding test can count as contract evidence. | R-13; readiness rule |
| 2.1A-UNIT-001 | P1 | Unit | Pure path normalization covers expand-user, relative/dot collapse, trailing separators, and root preservation. | R-02, R-12 |
| 2.1A-UNIT-002 | P1 | Unit | Pure GitHub-key derivation accepts the clarified owner/repo shape, canonicalizes case/order, and rejects partial/malformed shapes. | R-03 |
| 2.1A-UNIT-003 | P1 | Unit | Binding id generation follows the selected `pb_` random format and remains independent of profile/cwd/artifact values. | R-07, R-11 |

### Acceptance-Criterion Traceability

| Acceptance criterion | Atomic scenarios | Disposition |
| --- | --- | --- |
| AC1: authorized create persists all fields and stable identity after restart | INT-001, INT-002, INT-016, INT-027–INT-029, INT-040 | Covered at persistence boundary; authorization itself is W-01 because no public caller exists. |
| AC2: all uniqueness violations reject without partial write and return machine conflict | INT-010, INT-011, INT-013, INT-019–INT-024, INT-042 | Covered, including all dimensions, aggregation, duplicate action, constraint fail-safe, concurrency, and rollback. |
| AC3: read by id returns all fields exactly after restart | INT-002–INT-004, INT-015, INT-016, INT-026, INT-037, INT-039 | Covered with normal, unknown, profile-filtered, contract, Unicode, and corruption paths. |
| AC4: existing schema reopens idempotently/additively without data loss or duplicate errors | INT-030–INT-035 | Covered, including cached and new-process paths, concurrent init, stale cache, and schema relationships. |

### High-Risk Traceability

| Risk | Scenarios or waiver |
| --- | --- |
| R-01 | INT-005–INT-008 |
| R-02 | INT-009–INT-012, INT-019, INT-022, INT-035, UNIT-001 |
| R-03 | INT-013–INT-015, UNIT-002 |
| R-04 | INT-016–INT-019 |
| R-05 | INT-019–INT-021, INT-042 |
| R-06 | INT-023–INT-025 |
| R-07 | INT-001, INT-002, INT-037, INT-040, UNIT-003 |
| R-08 | INT-030–INT-035 |
| R-09 | INT-004, INT-022, INT-026–INT-029 |
| R-10 | INT-008, INT-014, INT-017, INT-037–INT-039, INT-042 |
| R-11 | INT-041, UNIT-003 |
| R-12 | INT-012, UNIT-001, plus W-09 for physical/case aliases |
| R-13 | All integration tests use real SQLite; INT-016, INT-035, INT-045, VAL-001 |
| R-14 | INT-025, INT-042–INT-045 |
| R-15 | W-10; no product threshold exists. |

### Reviewer-Concern Traceability

| Reviewer concern | Scenario or waiver |
| --- | --- |
| Random persisted id, not derived identity | INT-002, INT-040, UNIT-003 |
| Canonical GitHub key, not JSON equality | INT-013–INT-015, UNIT-002 |
| Collect every conflict dimension/id | INT-019, INT-020 |
| Database constraint remains race fail-safe | INT-023, INT-024 |
| No auto-suffix/dedupe/retry | INT-021 |
| Partial unique indexes preserve optional `NULL` | INT-009, INT-035 |
| Explicit profile despite per-profile DB | INT-004, INT-022, INT-026–INT-029 |
| Generic provider/name plus opaque metadata | INT-016–INT-019 |
| Migration on every connect and idempotent init | INT-030–INT-034 |
| Real SQLite, not mock-only | All `INT` scenarios; especially INT-024, INT-030, INT-042–INT-045 |
| Materialization readiness expectations | AC/risk matrices plus INT-019–INT-024, INT-030–INT-035, VAL-001 |
| Per-profile Projects-store ownership pattern | INT-027–INT-029, INT-045 |
| Do not create full seed or command/tool wiring | W-08 |
| Defer safety/lifecycle/provider health/BMAD mount | W-02–W-05 |
| External Archon producer output absent | W-07 |
| “Authorized command” wording without a command | W-01 |

### Explicit Coverage Waivers

| Waiver | Reason | Owner | Residual risk | Follow-up trigger |
| --- | --- | --- | --- | --- |
| W-01 Authorization/public command | Story 2.1a adds only an internal repository and explicitly forbids command/tool wiring. There is no actor/session boundary to authenticate here. | Owner of the first public create/read command/API/tool story | A future caller could expose create/read without an authorization check. | Any command, API route, model tool, gateway action, or agent action calls the repository. Add P0 authorized/unauthorized/cross-profile tests then. |
| W-02 Cwd exists/allowed-root/git validation | Explicit Story 2.1b scope; 2.1a only rejects blank structural identity and stores references. | Story 2.1b owner | Persisted but unvalidated cwd data is unsafe if consumed prematurely. | Before any workflow action accepts a binding; add missing/outside-root/non-git/symlink cases. |
| W-03 Update/disable/repair/re-enable/audit | Explicit Story 2.1c scope. | Story 2.1c owner | No mutable lifecycle or audit evidence exists in 2.1a. | When update/status/lifecycle methods are added. |
| W-04 Provider registration/health/rotation | Explicit Story 3.2 scope; 2.1a stores only structurally compatible opaque metadata. | Story 3.2 owner | Stored metadata can become stale, but is not interpreted here. | Any provider I/O, health classification, refresh, rotate, or conflict diagnosis is introduced. |
| W-05 BMAD skill mounting | Explicit Story 2.2 scope. | Story 2.2 owner | A stored skill-dir reference is not proof it is mounted or valid. | Any code mutates `skills.external_dirs` or invokes BMAD from the reference. |
| W-06 Cancellation/out-of-order/stale external events | Synchronous create/read has no queue, event timestamp, callback order, retry loop, or cancellation token. SQLite lock timeout is covered by INT-043. | Owner of the first async/event-driven binding operation | Later async orchestration could mishandle replay/order/cancellation. | Add event ingestion, background tasks, retries, cancellation, or timestamped binding commands. |
| W-07 External Archon runtime evidence | No provider result is consumed; local v1 fixture shape is stored opaquely and validated by VAL-001/INT-016. | Story 3.2/provider-integration owner | Local fixtures do not prove real Archon producer compatibility. | Before marking any provider-dependent consumer story done. |
| W-08 UI/API/E2E and full structural seed | Headless storage-only scope introduces no public/user surface and story notes forbid unrelated seed modules. | Product owner + future surface owner | User-journey/auth behavior remains untested until exposed. | A command/API/UI/tool is added or another seed module enters scope. |
| W-09 Symlink and platform case equivalence | Story prescribes textual `abspath + expanduser + trailing-strip`; physical identity (`realpath`) and Windows case-folding are not decided. | Architect + Story 2.1b owner | The same physical repo may be persisted through aliases on some platforms. | Architecture chooses physical-path identity, Windows CI exposes a collision miss, or Story 2.1b conflict detection starts. |
| W-10 Performance/scalability SLO | No binding-count, latency, busy-timeout, or writer-throughput threshold exists; inventing one would be a change-detector. | Product owner + operations | Large stores or heavy contention may regress unnoticed beyond bounded race tests. | Production contention, a specified SLO, or an expected scale envelope appears. |

### Edge-Class Audit

| Required class | Coverage |
| --- | --- |
| Happy path | INT-001, INT-002, INT-009, INT-016, INT-018, INT-025 |
| Negative path | INT-003, INT-005–INT-008, INT-014, INT-017, INT-019–INT-021 |
| Boundary cases | INT-009, INT-012, INT-022, INT-041, UNIT-001 |
| Malformed input/data | INT-008, INT-014, INT-017, INT-038, INT-039 |
| Stale data/cache | INT-034; provider staleness is W-04 |
| Duplicate actions | INT-021 |
| Out-of-order events | W-06 |
| Partial failure | INT-020, INT-042 |
| Dependency failure | INT-043–INT-045 |
| Timeout | INT-043 |
| Cancellation | W-06 |
| Concurrency/race | INT-023–INT-025, INT-033 |
| Rollback | INT-042, INT-043 |
| Permission/auth | Filesystem/path failure INT-044; actor authorization W-01 |
| Regression | INT-021, INT-030–INT-034, INT-040, INT-045 |

### NFR Evidence Plan

| NFR | Planned evidence | Later evidence artifact |
| --- | --- | --- |
| Security/profile isolation | INT-004, INT-022, INT-026–INT-029; W-01 tracks public auth. | Focused pytest/JUnit results and profile-path assertions. |
| Reliability/data integrity | INT-002, INT-019–INT-025, INT-030–INT-043. | Pytest results plus failure output showing row-count, restart, and race invariants. |
| Compatibility/migration | INT-016, INT-030–INT-035, INT-045, VAL-001. | Contract-validator output and pytest/JUnit results. |
| Maintainability | Unit/helper tests plus behavior-contract integration tests; no mutable enumeration snapshots. | CI test results, Ruff output, and review of new-module coverage. |
| Performance/scalability | Threshold UNKNOWN; W-10. | None until a threshold is approved; bounded race evidence is reliability-only. |

### Execution Strategy

- **PR:** Run `scripts/run_tests.sh tests/project_work/test_bindings.py`, the contract validator, and Ruff on the new package/tests. All deterministic P0/P1 scenarios belong here and should remain well below 15 minutes.
- **Nightly:** Run the focused file together with existing SQLite/kanban concurrency and stress coverage across supported operating systems; repeat the multi-process race inside a bounded test loop to expose timing defects without sleeps as assertions.
- **Weekly:** Run the complete isolated Python suite. No performance/chaos job is authorized until W-10 has a measurable threshold.

### Resource Estimate

| Priority | Estimate |
| --- | --- |
| P0 automation and ambiguity resolution | ~12–20 hours |
| P1 automation, fault injection, migration, and concurrency | ~20–36 hours |
| P2 resource/maintenance checks | ~3–6 hours |
| P3 exploratory/benchmark work | ~0–2 hours |
| **Total** | **~35–64 hours (about 5–8 engineering days)** |

### Quality Gates

- P0 pass rate: **100%**; R-01 through R-04 contract ambiguities resolved before implementation sign-off.
- Deterministic P1 data-integrity/compatibility tests: **100% for merge** (stricter than the generic 95% threshold); no quarantined race test counts as evidence.
- Acceptance-criterion, P0/P1-risk, and reviewer-concern mapping: **100% scenario or complete waiver**.
- New-module automated code coverage: **≥80% if coverage is collected**, while behavior/risk traceability remains the authoritative target.
- Contract validator and focused isolated pytest suite: pass with no escaped `IntegrityError`, leaked transaction, duplicate row, or data-loss failure.
- All high-risk mitigations must be implemented before story completion; full NFR PASS/CONCERNS/FAIL remains deferred to `nfr-assess` after code and execution evidence exist.

## Step 5: Output Generation and Validation

- **Resolved execution mode:** Sequential. The run is epic-level with one output artifact; the user did not request agent-team or subagent execution.
- **Output:** `_bmad-output/test-artifacts/test-design-epic-2.1a.md`
- **Result:** 49 conceptual automated scenarios: 4 P0, 44 P1, 1 P2, and 0 P3. Parameterized inputs and uniqueness dimensions must remain independently reported pytest nodes.
- **Risk result:** 15 scored risks, including 12 score ≥6 and two critical-domain promotions to P1. R-001–R-004 are score-9 contract blockers.
- **Mandatory traceability:** All four acceptance criteria, all 15 risks, and all known reviewer concerns map to atomic scenarios or W-01–W-10 waivers with reason, owner, residual risk, and trigger.
- **Coverage breadth:** Happy, negative, boundary, malformed, stale, duplicate, out-of-order, partial/dependency failure, timeout, cancellation, concurrency/race, rollback, permission/auth, and regression classes are covered or explicitly waived.
- **Gate:** P0 and deterministic P1 must pass at 100%; no open P0/P1 defect or unresolved R-001–R-004 decision is compatible with story completion.
- **Checklist validation:** Risk IDs/scores, scenario IDs/counts, AC/risk/reviewer mappings, NFR evidence plan, PR/nightly/weekly strategy, range estimates, entry/exit criteria, residual risks, and Markdown structure were checked. The prerequisite “requirements are unambiguous” remains intentionally unchecked because R-001–R-004 are explicit blockers; the artifact is therefore Draft, not Approved.
- **Session hygiene:** No browser/Playwright session was opened. Workflow artifacts are contained under `_bmad-output/test-artifacts/`.
- **Open assumptions:** No public caller exists in this story; physical path alias equivalence and performance thresholds remain owned by W-09 and W-10.
