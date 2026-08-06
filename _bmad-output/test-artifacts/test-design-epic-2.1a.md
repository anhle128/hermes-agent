---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted:
  - 'step-01-detect-mode'
  - 'step-02-load-context'
  - 'step-03-risk-and-testability'
  - 'step-04-coverage-plan'
  - 'step-05-generate-output'
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-07-13'
---

# Test Design: Story 2.1a - Create and Persist Project Bindings

**Date:** 2026-07-13  
**Author:** Kevin  
**Mode:** Epic-Level, scoped to Story 2.1a  
**Status:** Draft — pre-implementation P0 contract decisions open

## Executive Summary

This plan covers the new `hermes_project_work.bindings` persistence boundary: schema creation, create/read behavior, stable restart identity, profile-scoped uniqueness, additive reopen, contract-compatible provider metadata, and failure atomicity. The implementation and test package do not yet exist.

The plan contains 49 conceptual automated scenarios. Parameterized scenarios must emit a separate pytest node for each listed malformed input or uniqueness dimension.

| Summary | Value |
| --- | --- |
| Risks | 15 total; 12 score ≥6; 2 critical-domain promotions to P1 |
| Blocking decisions | R-001 required-field behavior, R-002 uniqueness contract, R-003 GitHub input shape, R-004 provider structural identity |
| Scenarios | 4 P0, 44 P1, 1 P2, 0 P3 |
| Primary level | Python integration tests with real SQLite files under `tmp_path` |
| Estimated effort | ~35–64 hours, about 1–2 engineering weeks |
| Gate posture | Planned coverage is traceable; implementation readiness is blocked until R-001–R-004 are resolved |

## Not in Scope and Waivers

Every exclusion has an owner, residual risk, and trigger. These waivers do not authorize a later surface to omit its own tests.

| Waiver | Reason | Owner | Residual risk | Follow-up trigger |
| --- | --- | --- | --- | --- |
| W-01 Authorization/public caller | Story 2.1a adds an internal repository only and explicitly excludes command/tool wiring. | First public create/read surface owner | A future command/API/tool could expose mutation without authorization. | Any command, API, tool, gateway action, or agent action calls this repository; add P0 authorized, unauthorized, and cross-profile tests. |
| W-02 Cwd safety validation | Existence, allowed roots, and git-repo checks belong to Story 2.1b. Blank structural identity is still covered here. | Story 2.1b owner | Persisted unvalidated cwd data is unsafe if consumed early. | Before any workflow action consumes a binding. |
| W-03 Lifecycle/audit | Update, disable, repair, re-enable, validation state, and audit history belong to Story 2.1c. | Story 2.1c owner | No mutable lifecycle evidence exists in this story. | When lifecycle methods are added. |
| W-04 Provider lifecycle/health | Registration, refresh, status, rotation, and conflict diagnosis belong to Story 3.2. | Story 3.2 owner | Opaque stored metadata may become stale. | Any provider I/O or status interpretation is introduced. |
| W-05 BMAD mounting | `skills.external_dirs` mutation and mount validation belong to Story 2.2. | Story 2.2 owner | A stored skill-dir reference is not proof of a usable mount. | Any code mounts or invokes BMAD from this reference. |
| W-06 Async order/cancellation | Synchronous create/read has no queue, event order, callback timestamp, retry loop, or cancellation token. SQLite lock timeout is covered. | First async binding-operation owner | Later async orchestration could mishandle replay/order/cancellation. | Add events, background work, retries, or cancellation. |
| W-07 External Archon runtime | This story stores a local v1 fixture opaquely and consumes no live provider result. | Provider-integration owner | Local fixtures do not prove real producer compatibility. | Before any provider-dependent story is marked done. |
| W-08 UI/API/E2E and full seed | No public surface exists, and unrelated project-work modules are explicitly out of scope. | Future surface/product owner | User-journey behavior remains untested until a surface exists. | A public surface or another seed module enters scope. |
| W-09 Symlink/Windows case equivalence | The story prescribes textual `abspath + expanduser + trailing-strip`; physical identity is undecided. | Architect + Story 2.1b owner | The same physical repo can be represented by aliases. | Physical-path identity is approved, Windows CI exposes a collision miss, or Story 2.1b starts. |
| W-10 Performance/scalability SLO | No binding-count, latency, lock-wait, or throughput threshold exists. | Product owner + operations | Large stores or heavy contention may regress beyond bounded race checks. | Production contention or an approved scale/SLO requirement appears. |

## Risk Assessment

Probability and impact use the TEA 1–3 scale; score is `P × I`. Score 9 is P0. Score 6–8 is P1. Lower scores are promoted to P1 when failure can still break core behavior, data integrity, security, compatibility, or cross-process behavior.

**Category legend:** DATA = data integrity, TECH = architecture/integration, SEC = security/isolation, OPS = operational reliability, PERF = performance/scalability. No BUS risk is asserted because the supplied evidence defines no revenue or adoption impact.

### Testability and Contract Clarity

| Dimension | Assessment | Evidence/action |
| --- | --- | --- |
| Controllability | Strong after implementation | Explicit DB paths, `tmp_path`, dependency seams, and spawned workers can drive every persistence state without a public UI/API. |
| Observability | Strong for persisted invariants; blocked for four input contracts | Rows, indexes, transactions, returned outcomes, restart state, and process results are observable. R-001–R-004 require decisions before expected results are authoritative. |
| Reliability | Strong with real SQLite | Existing tests demonstrate temp-file, reopen, barrier, and multi-process patterns. No sleep-based assertion or mock-only database evidence is accepted. |
| Ambiguity | **Blocking** | Required blank-value behavior, uniqueness details, GitHub reference shape, and provider structural identity must be resolved under R-001–R-004. The document remains Draft until then. |

### High-Priority Risks (Score ≥6)

| ID | Cat. | Risk | P | I | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| R-001 | DATA | Blank required values can satisfy SQL `NOT NULL`; blank cwd can normalize to the process cwd. | 3 | 3 | 9 | Reject blank required identity before normalization/SQL and prove zero mutation. | Dev + Product | Before coding/merge |
| R-002 | DATA | Path spelling, profile scope, optional `NULL`, or incorrect index predicates can bypass or over-enforce uniqueness. | 3 | 3 | 9 | Define normalized keys and four profile-scoped persistence constraints; test each boundary. | Dev + QA | Before merge |
| R-003 | DATA | GitHub reference input shape and canonicalization are undefined; JSON text equality misses semantic duplicates. | 3 | 3 | 9 | Approve a minimal owner/repo contract, canonicalize semantic values, reject partial shapes. | Product + Architect | Before key implementation |
| R-004 | TECH | Provider metadata may omit/disagree with generic provider/name Controller Identity. | 3 | 3 | 9 | Require a complete, consistent tuple when metadata exists; round-trip the real v1 fixture. | Architect + Dev | Before merge |
| R-005 | DATA | Multi-dimensional conflicts may report only the first constraint, auto-suffix, retry, or partially mutate. | 2 | 3 | 6 | Pre-check all dimensions in one IMMEDIATE transaction and return every dimension→id. | Dev | Before merge |
| R-006 | DATA | Concurrent writers may both pass an application pre-check without database serialization/constraints. | 2 | 3 | 6 | Real spawned-process race; exactly one row, one success, one structured conflict. | Dev + QA | Before merge/nightly burn-in |
| R-007 | DATA | Restart may recompute identity or lose exact nullable/JSON fields. | 2 | 3 | 6 | Close/reopen and compare the id plus every public field and `to_dict()`. | Dev | Before merge |
| R-008 | TECH | `_INITIALIZED_PATHS` may suppress migration, race at first connect, or become stale after file replacement. | 2 | 3 | 6 | Test every-connect migration, cached/new-process/concurrent paths, and stale cache. | Dev | Before merge |
| R-009 | OPS/SEC | Wrong `HERMES_HOME` routing can write project context into the wrong profile DB. | 2 | 3 | 6 | Test profile-aware paths, self-describing profile rows, filtered reads, and separate homes. | Dev + Security reviewer | Before merge |
| R-010 | TECH/DATA | Non-serializable/non-standard/corrupt JSON can partially write, break reads, or be misreported as conflict. | 2 | 3 | 6 | Strict serialization, pre-write rejection, explicit corruption failure, rollback evidence. | Dev | Before merge |
| R-012 | TECH/DATA | Textual normalization does not decide symlink or platform case equivalence. | 2 | 3 | 6 | Test the documented textual contract; W-09 owns the physical-identity decision. | Architect + Product | Before merge decision |
| R-013 | TECH | Mock-only or snapshot tests can miss actual SQLite, migration, WAL, and contract behavior. | 2 | 3 | 6 | Real temp DBs, real imports, behavior assertions, real contract fixture and validator. | QA + Dev | Before merge |

### Medium Risks and Critical-Domain Promotions

| ID | Cat. | Risk | P | I | Score | Priority | Mitigation | Owner |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| R-011 | DATA | A rare random-id collision could overwrite/misclassify a distinct binding. | 1 | 3 | 3 | P1 | Inject the collision; preserve the first row and use an explicit internal-id outcome. | Dev |
| R-014 | OPS/DATA | DB-open, WAL, lock, or insert failure may mask the cause, leak a transaction, or partially mutate. | 2 | 2 | 4 | P1 | Inject insert/dependency failure, force lock timeout, prove rollback and later reuse. | Dev |

### Low Risk

| ID | Cat. | Risk | P | I | Score | Action |
| --- | --- | --- | ---: | ---: | ---: | --- |
| R-015 | PERF/OPS | No latency, scale, busy-timeout, or writer-throughput target exists. | 1 | 2 | 2 | Track through W-10; do not invent an SLO. |

### Residual Risk After Planned Mitigation

| Risk | Residual risk |
| --- | --- |
| R-001–R-004 | None is accepted before the four contract decisions are recorded and their P0/P1 scenarios pass; until then, implementation readiness remains blocked. |
| R-005–R-006 | Out-of-band database mutation or filesystem corruption can bypass repository conflict semantics; database constraints and explicit corruption errors limit, but cannot eliminate, this risk. |
| R-007–R-010 | Manual DB edits, unsupported future schema changes, or wrong-home process configuration can still cause drift; restart, migration, strict parsing, and isolation tests reduce the supported-path risk. |
| R-011 | Random collision remains theoretically possible; the explicit collision policy must fail closed without overwriting data. |
| R-012 | Physical aliases remain an accepted unresolved risk only under W-09 until path-identity semantics are approved. |
| R-013 | Tests cannot prove every filesystem/SQLite implementation variation; supported runtimes and OS CI define the evidence boundary. |
| R-014 | Host crashes and disk-full behavior outside SQLite's guarantees remain; repository-level rollback, timeout, dependency, and recovery paths must still pass. |
| R-015 | Performance risk remains unknown and accepted only under W-10 until a measurable threshold or production signal appears. |

## Reviewer Concern Disposition

The latest readiness review contains no separate defect against Story 2.1a. The concerns below are the load-bearing warnings embedded in the story, architecture, and contract readiness rules.

| Concern | Classification | Scenario or waiver |
| --- | --- | --- |
| Random persisted id; never derive identity from cwd/artifacts | Risk R-007/R-011 | INT-002, INT-040, UNIT-003 |
| Canonical GitHub key; never compare JSON text | Risk R-003 | INT-013–INT-015, UNIT-002 |
| Return all collided dimensions and ids | Risk R-005 | INT-019, INT-020 |
| Retain database constraints as race fail-safe | Risk R-006 | INT-023, INT-024 |
| Never auto-suffix, dedupe, or retry ambiguous create | Risk R-005 | INT-021 |
| Partial unique indexes must preserve optional `NULL` | Risk R-002 | INT-009, INT-035 |
| Keep explicit profile even in per-profile DB | Risk R-009 | INT-004, INT-022, INT-026–INT-029 |
| Use generic provider/name and opaque metadata | Risk R-004 | INT-016–INT-019 |
| Run migration on every connect; keep init idempotent | Risk R-008 | INT-030–INT-034 |
| Use real SQLite, not mock-only tests | Risk R-013 | All INT scenarios; especially INT-024, INT-030, INT-042–INT-045 |
| Carry migration/uniqueness/idempotency readiness expectations | Risk R-013 | INT-019–INT-024, INT-030–INT-035, VAL-001 |
| Follow per-profile Projects-store ownership, not shared Kanban ownership | Risk R-009/R-013 | INT-027–INT-029, INT-045 |
| Do not create full seed or command/tool wiring | Explicit non-risk | W-08 |
| Defer cwd safety/lifecycle/provider health/BMAD mount | Explicit non-risk | W-02–W-05 |
| External Archon producer evidence is absent | Explicit non-risk for this story | W-07 |
| AC1 says authorized command, but no public caller exists | Explicit non-risk with trigger | W-01 |

## NFR Planning

This section plans later evidence; it does not declare final NFR PASS/CONCERNS/FAIL.

| NFR | Requirement/threshold | Risk | Planned validation | Evidence for later `nfr-assess` |
| --- | --- | --- | --- | --- |
| Security/profile isolation | No public surface in this story; profile homes/rows must remain isolated. | R-009; W-01 | INT-004, INT-022, INT-026–INT-029 | Focused pytest/JUnit output and path/profile assertions |
| Reliability/data integrity | Restart exactness; conflicts/failures persist zero extra rows; race persists exactly one same-key row. | R-001, R-002, R-005–R-011, R-014 | INT-002, INT-019–INT-025, INT-030–INT-043 | Pytest/JUnit output with row-count, restart, race, and rollback invariants |
| Compatibility/migration | Current schema reopens; migration runs every connect; v1 fixture vocabulary remains intact. | R-004, R-008, R-013 | INT-016, INT-030–INT-035, INT-045, VAL-001 | Contract-validator and pytest output |
| Maintainability | Use existing helpers/patterns and behavior contracts; avoid mutable enumeration snapshots. | R-013 | UNIT scenarios, INT-035, focused Ruff/checks | Ruff, coverage if collected, focused test report |
| Performance/scalability | **UNKNOWN** — no product threshold. | R-015 | W-10; bounded concurrency is reliability evidence only. | None until an SLO/scale envelope is approved |
| Compliance | Not specified. | — | N/A | N/A |

## Entry Criteria

- [ ] Product/architecture decisions for R-001–R-004 are recorded in the story or implementation contract.
- [ ] `hermes_project_work/bindings.py` and `tests/project_work/test_bindings.py` exist with the intended public signatures.
- [ ] Supported project Python (`>=3.11,<3.14`) and the repository environment are available.
- [ ] Tests use explicit `tmp_path / "project_bindings.db"`; profile-routing tests use context-local/temp Hermes homes.
- [ ] The local Workflow Commander contract package and `status-valid.json` fixture remain available.
- [ ] No public command/API/tool is introduced under Story 2.1a without reopening W-01/W-08.

## Exit Criteria

- [ ] P0 and deterministic P1 pass at 100%; no race test is quarantined or treated as optional.
- [ ] All four ACs, all P0/P1 risks, and all reviewer concerns retain a scenario or complete waiver.
- [ ] No open P0/P1 defect affects data integrity, profile isolation, migration, contract compatibility, or transaction behavior.
- [ ] Contract validator, focused isolated pytest suite, and Ruff pass.
- [ ] No escaped uniqueness `IntegrityError`, duplicate binding, partial write, stale-cache `no such table`, or restart field drift remains.
- [ ] NFR evidence sources are produced; final NFR judgment is deferred to `nfr-assess`.

## Test Coverage Plan

P0/P1/P2/P3 indicate risk priority, not execution timing. Run everything in PRs when the focused suite remains under 15 minutes. Parameterized inputs/dimensions below must be separate pytest cases.

### P0 — Blocking Contract/Data Cases

| Test ID | Atomic scenario | Level | Trace | Owner |
| --- | --- | --- | --- | --- |
| 2.1A-INT-007 | Reject blank cwd before normalization; zero mutation. | Integration | R-001 | Dev/QA |
| 2.1A-INT-013 | Semantically equal GitHub references with reordered/case-varied owner/repo collide. | Integration | AC2, R-003 | Dev/QA |
| 2.1A-INT-017 | Reject each partial/blank/inconsistent provider identity shape; zero mutation. | Integration | R-004, R-010 | Dev/QA |
| 2.1A-INT-019 | Each uniqueness dimension independently returns its dimension and existing id, with one row and no escaped error. | Integration | AC2, R-002, R-005 | Dev/QA |

**P0 count:** 4 conceptual scenarios.

### P1 — Core, Compatibility, Failure, and Regression Cases

| Test ID | Atomic scenario | Level | Trace | Owner |
| --- | --- | --- | --- | --- |
| 2.1A-INT-001 | Fresh all-field create persists one normalized row and returns stable id/success. | Integration | AC1, R-001, R-007 | Dev/QA |
| 2.1A-INT-002 | New connection reads the unchanged id and every public field exactly. | Integration | AC1, AC3, R-007 | Dev/QA |
| 2.1A-INT-003 | Unknown binding id returns `None` without mutation. | Integration | AC3 | Dev/QA |
| 2.1A-INT-004 | Profile list returns only that profile and every public field. | Integration | AC3, R-009 | Dev/QA |
| 2.1A-INT-005 | Reject blank profile; zero mutation. | Integration | R-001 | Dev/QA |
| 2.1A-INT-006 | Reject blank display name; zero mutation. | Integration | R-001 | Dev/QA |
| 2.1A-INT-008 | Reject each `None`/unsupported required-field type without conflict misclassification. | Integration | R-001, R-010 | Dev/QA |
| 2.1A-INT-009 | Multiple distinct rows with all optional references `NULL` are allowed. | Integration | AC1, R-002 | Dev/QA |
| 2.1A-INT-010 | Equivalent cwd spellings collide within one profile. | Integration | AC2, R-002 | Dev/QA |
| 2.1A-INT-011 | Equivalent BMAD-dir spellings collide within one profile. | Integration | AC2, R-002 | Dev/QA |
| 2.1A-INT-012 | Filesystem root remains root after normalization. | Integration | R-002, R-012 | Dev/QA |
| 2.1A-INT-014 | Reject each malformed/partial GitHub reference; zero mutation. | Integration | R-003, R-010 | Dev/QA |
| 2.1A-INT-015 | Preserve valid GitHub JSON exactly while using a separate canonical key. | Integration | AC3, R-003 | Dev/QA |
| 2.1A-INT-016 | Load real provider fixture, persist generic tuple/metadata, restart, and compare exactly. | Contract integration | AC1, AC3, R-004, R-013 | Dev/QA |
| 2.1A-INT-018 | Distinct complete provider/name tuples are allowed. | Integration | R-004 | Dev/QA |
| 2.1A-INT-020 | Candidate colliding on all four dimensions returns all dimension→id entries and no row. | Integration | AC2, R-005 | Dev/QA |
| 2.1A-INT-021 | Exact duplicate action conflicts; no suffix, retry, or extra row. | Integration | AC2, R-005 | Dev/QA |
| 2.1A-INT-022 | Same identity values under different profiles are allowed in one DB. | Integration | AC2, R-002, R-009 | Dev/QA |
| 2.1A-INT-023 | Forced pre-check miss still becomes structured conflict through real unique index. | Integration | AC2, R-006 | Dev/QA |
| 2.1A-INT-024 | Two processes race on one identity: one success, one conflict, one row. | Cross-process integration | AC2, R-006 | Dev/QA |
| 2.1A-INT-025 | Two processes create distinct identities: both persist/read after reopen. | Cross-process integration | R-006, R-014 | Dev/QA |
| 2.1A-INT-026 | Mixed-profile explicit DB list filters correctly. | Integration | AC3, R-009 | Dev/QA |
| 2.1A-INT-027 | DB path resolves under each context-local/temp profile home. | Integration | R-009 | Dev/QA |
| 2.1A-INT-028 | Active profile stores correctly; resolver exception stores documented `default`. | Integration | AC1, R-009 | Dev/QA |
| 2.1A-INT-029 | Separate profile homes cannot read each other's bindings. | Integration | AC1, R-009 | Dev/QA |
| 2.1A-INT-030 | Reopen current schema twice without data loss/schema error. | Integration | AC4, R-008 | Dev/QA |
| 2.1A-INT-031 | Migration seam is invoked on every connect, including cached schema. | Integration | AC4, R-008 | Dev/QA |
| 2.1A-INT-032 | Clear init cache/new-process simulation preserves schema/data. | Integration | AC4, R-008 | Dev/QA |
| 2.1A-INT-033 | Concurrent first connects all close cleanly and leave usable schema. | Threaded integration | AC4, R-008 | Dev/QA |
| 2.1A-INT-034 | Cached path whose DB file is recreated does not produce `no such table`. | Integration | R-008 | Dev/QA |
| 2.1A-INT-035 | PRAGMA relationships prove required columns and four unique predicates without count snapshots. | Integration | AC4, R-002, R-008 | Dev/QA |
| 2.1A-INT-037 | Nested Unicode/JSON null/arrays survive exact restart round-trip. | Integration | AC3, R-007, R-010 | Dev/QA |
| 2.1A-INT-038 | Reject non-serializable and non-standard JSON constants before insert. | Integration | R-010 | Dev/QA |
| 2.1A-INT-039 | Corrupt stored JSON fails explicitly rather than silently substituting data. | Integration | R-010 | Dev/QA |
| 2.1A-INT-040 | Stored id is not recomputed from changed/reordered input variables. | Integration | AC1, R-007 | Dev/QA |
| 2.1A-INT-041 | Forced random-id collision preserves first row and follows explicit internal-id policy. | Integration | R-011 | Dev/QA |
| 2.1A-INT-042 | Inject insert failure; original error, rollback, zero row, and later reuse. | Integration | AC2, R-005, R-010, R-014 | Dev/QA |
| 2.1A-INT-043 | Held IMMEDIATE lock causes bounded timeout/no write; create succeeds after release. | Integration | R-014 | Dev/QA |
| 2.1A-INT-044 | Invalid parent path fails without cache poison; later valid path works. | Integration | R-014 | Dev/QA |
| 2.1A-INT-045 | Foreign keys are on and journal mode is WAL or documented DELETE fallback. | Integration | R-013, R-014 | Dev/QA |
| 2.1A-VAL-001 | Shipped Workflow Commander contract validator passes. | Contract validation | R-013 | Dev/QA |
| 2.1A-UNIT-001 | Path helper covers expand-user, relative/dot, trailing separator, and root. | Unit | R-002, R-012 | Dev/QA |
| 2.1A-UNIT-002 | GitHub-key helper canonicalizes approved shape and rejects malformed shapes. | Unit | R-003 | Dev/QA |
| 2.1A-UNIT-003 | Random id format is independent of profile/cwd/artifact values. | Unit | R-007, R-011 | Dev/QA |

**P1 count:** 44 conceptual scenarios.

### P2 — Resource Hygiene

| Test ID | Atomic scenario | Level | Trace | Owner |
| --- | --- | --- | --- | --- |
| 2.1A-INT-036 | `connect_closing()` closes the SQLite connection after context exit. | Integration | Maintainability | Dev/QA |

**P2 count:** 1. **P3:** none.

## Mandatory Traceability

### Acceptance Criteria

| AC | Atomic scenarios | Result |
| --- | --- | --- |
| AC1 | INT-001, INT-002, INT-009, INT-016, INT-027–INT-029, INT-040 | Covered at persistence boundary; public authorization is W-01. |
| AC2 | INT-010, INT-011, INT-013, INT-019–INT-024, INT-042 | Covered across all dimensions, aggregation, duplicates, fail-safe, race, and rollback. |
| AC3 | INT-002–INT-004, INT-015, INT-016, INT-026, INT-037, INT-039 | Covered for exact, unknown, filtered, contract, Unicode, and corruption reads. |
| AC4 | INT-030–INT-035 | Covered for cached/new-process/concurrent/stale/schema-relation paths. |

### High Risks

| Risk | Scenarios/waiver |
| --- | --- |
| R-001 | INT-005–INT-008 |
| R-002 | INT-009–INT-012, INT-019, INT-022, INT-035, UNIT-001 |
| R-003 | INT-013–INT-015, UNIT-002 |
| R-004 | INT-016–INT-019 |
| R-005 | INT-019–INT-021, INT-042 |
| R-006 | INT-023–INT-025 |
| R-007 | INT-001, INT-002, INT-037, INT-040, UNIT-003 |
| R-008 | INT-030–INT-035 |
| R-009 | INT-004, INT-022, INT-026–INT-029 |
| R-010 | INT-008, INT-014, INT-017, INT-037–INT-039, INT-042 |
| R-011 | INT-041, UNIT-003 |
| R-012 | INT-012, UNIT-001, W-09 |
| R-013 | All integration tests use real SQLite; INT-016, INT-035, INT-045, VAL-001 |
| R-014 | INT-025, INT-042–INT-045 |
| R-015 | W-10 |

### Edge-Class Audit

| Class | Coverage |
| --- | --- |
| Happy | INT-001, INT-002, INT-009, INT-016, INT-018, INT-025 |
| Negative | INT-003, INT-005–INT-008, INT-014, INT-017, INT-019–INT-021 |
| Boundary | INT-009, INT-012, INT-022, INT-041, UNIT-001 |
| Malformed | INT-008, INT-014, INT-017, INT-038, INT-039 |
| Stale | INT-034; provider staleness is W-04 |
| Duplicate action | INT-021 |
| Out-of-order events | W-06 |
| Partial failure | INT-020, INT-042 |
| Dependency failure | INT-043–INT-045 |
| Timeout | INT-043 |
| Cancellation | W-06 |
| Concurrency/race | INT-023–INT-025, INT-033 |
| Rollback | INT-042, INT-043 |
| Permission/auth | Filesystem dependency INT-044; actor authorization W-01 |
| Regression | INT-021, INT-030–INT-034, INT-040, INT-045 |

## Execution Strategy

Run everything in PRs when the focused suite remains below 15 minutes; defer only genuinely expensive or repeated work.

- **PR:** Run the contract validator and focused Ruff checks, then P0, P1, and P2 scenarios through `scripts/run_tests.sh tests/project_work/test_bindings.py`. This order gives fast contract feedback without omitting lower-priority functional coverage.
- **Nightly:** Focused bindings tests plus existing SQLite/kanban concurrency and stress coverage across supported operating systems; bounded repeated race execution.
- **Weekly:** Complete isolated Python suite. No performance/chaos job until W-10 gains a measurable threshold.
- **Playwright:** N/A for this storage-only Python story; there is no browser surface or Playwright suite to parallelize.

## Resource Estimates

Estimates include ambiguity resolution, fixtures, fault injection, cross-process setup, and review.

| Priority | Effort range |
| --- | --- |
| P0 | ~12–20 hours |
| P1 | ~20–36 hours |
| P2 | ~3–6 hours |
| P3 | ~0–2 hours |
| **Total** | **~35–64 hours, about 1–2 engineering weeks** |

### Prerequisites

- `tmp_path` binding DB fixture with guaranteed close/cleanup.
- Factories for valid binding inputs and one collision per uniqueness dimension.
- Real contract fixture loader for `status-valid.json`.
- Spawn-safe worker helper for cross-process create races.
- Fault-injection wrapper around a real SQLite connection; no mock-only persistence suite.
- Supported project venv, `scripts/run_tests.sh`, pytest, Ruff, and the shipped contract validator.

## Quality Gate Criteria

- P0 pass rate: **100%**.
- Deterministic P1 pass rate: **100% for merge**; this is stricter than the generic ≥95% baseline because the cases protect data integrity and compatibility.
- P2 pass rate: **≥90%**, with triage for any failure.
- R-001–R-004 decisions and all score≥6 mitigations: complete before story completion.
- AC, P0/P1-risk, reviewer-concern coverage: **100% scenario or complete waiver**.
- New module automated code coverage: **≥80% if coverage is collected**; behavior/risk traceability remains authoritative.
- Contract validator, focused isolated pytest, and Ruff pass.
- Full NFR judgment remains deferred to `nfr-assess` after implementation evidence exists.

## Mitigation Plans

| Risk | Strategy | Verification | Owner | Timeline | Status |
| --- | --- | --- | --- | --- | --- |
| R-001 | Approve non-blank required-field contract; validate before normalization/SQL. | INT-005–INT-008 | Dev + Product | Before coding | Planned |
| R-002 | Implement normalized keys and four profile-scoped partial unique constraints. | INT-009–INT-012, INT-019, INT-022, INT-035, UNIT-001 | Dev + QA | Before merge | Planned |
| R-003 | Define structured GitHub owner/repo shape and canonical key. | INT-013–INT-015, UNIT-002 | Product + Architect | Before key code | Blocked on decision |
| R-004 | Define complete provider/name structural input and tuple/blob agreement. | INT-016–INT-019 | Architect + Dev | Before coding | Blocked on decision |
| R-005 | Aggregate pre-check conflicts in one IMMEDIATE transaction; never suffix/retry. | INT-019–INT-021, INT-042 | Dev | Before merge | Planned |
| R-006 | Keep DB constraints and exercise real cross-process writers. | INT-023–INT-025 | Dev + QA | Before merge/nightly | Planned |
| R-007 | Persist random id once and exact JSON/path fields; compare after restart. | INT-001, INT-002, INT-037, INT-040, UNIT-003 | Dev | Before merge | Planned |
| R-008 | Separate cached DDL initialization from every-connect migration; recover stale cache. | INT-030–INT-035 | Dev | Before merge | Planned |
| R-009 | Resolve profile/home through existing helpers and keep row profile explicit. | INT-004, INT-022, INT-026–INT-029 | Dev + Security reviewer | Before merge | Planned |
| R-010 | Enforce strict serialization and explicit corruption/failure behavior. | INT-008, INT-014, INT-017, INT-037–INT-039, INT-042 | Dev | Before merge | Planned |
| R-012 | Test textual normalization; make physical alias behavior explicit through W-09. | INT-012, UNIT-001, W-09 | Architect + Product | Before merge decision | Planned |
| R-013 | Use real SQLite/contract evidence and behavior assertions. | All INT tests, VAL-001, Ruff | QA + Dev | Before merge | Planned |

## Assumptions and Dependencies

### Assumptions

1. Story 2.1a remains storage-only and exposes no public command/API/tool.
2. Optional GitHub/BMAD/provider references may be absent; when provider metadata is present, structural provider/name completeness must be decided before code.
3. `ProjectBinding` uses a random persisted id; Project Work Item derived-identity rules do not apply.
4. Physical-path alias equivalence is deferred under W-09; documented textual normalization remains testable now.
5. Test design completion means the plan is complete, not that implementation/NFR evidence is complete.

### Dependencies

1. Story 2.1a product/architecture clarification for R-001–R-004 before implementation sign-off.
2. Local Workflow Commander provider-binding schema, valid fixture, and contract validator.
3. Existing `hermes_cli.sqlite_util`, `hermes_state.apply_wal_with_fallback`, profile, and Hermes-home helpers.
4. Supported Python project environment and isolated test runner.

### Risks to the Plan

- If the public function signatures choose separate provider fields instead of one structured input, INT-017 must be adapted while preserving complete tuple/agreement behavior.
- If the GitHub reference contract is not clarified, R-003 remains a P0 blocker and tests must not guess field aliases.
- If `scripts/run_tests.sh` cannot run the spawned-process test reliably on one OS, fix the worker/test harness; do not waive R-006 or replace it with a mock.

## Interworking and Regression

| Component | Impact | Regression scope |
| --- | --- | --- |
| `hermes_project_work.bindings` | New persistence boundary | Entire focused bindings suite |
| `hermes_cli.sqlite_util` | Shared transaction/migration helpers | Existing sqlite-util/kanban migration and rollback tests |
| `hermes_state.apply_wal_with_fallback` | Journal-mode dependency | Existing WAL fallback tests plus INT-045 wiring |
| `hermes_constants` / profile helpers | DB routing and row identity | Existing profile isolation/home tests plus INT-027–INT-029 |
| Workflow Commander contracts | Stored provider vocabulary/readiness | Contract validator plus INT-016 |
| `hermes_cli.projects_db` | Structural analog only; no modification expected | `tests/hermes_cli/test_projects_db.py` remains green |

## Follow-on Workflows (Manual)

- Run ATDD separately to scaffold failing P0 tests after R-001–R-004 are resolved.
- Run test automation expansion after implementation exists.
- Run NFR assessment only after execution evidence exists.

## Approval

- [ ] Product owner: required-field and GitHub contract decisions
- [ ] Architect/tech lead: provider identity and path-equivalence decisions
- [ ] QA/test architect: atomic coverage and waiver review
- [ ] Developer: feasibility and fixture/fault-injection review

## Appendix: References

### Knowledge Base

- `risk-governance.md`
- `probability-impact.md`
- `test-levels-framework.md`
- `test-priorities-matrix.md`
- `nfr-criteria.md`
- `contract-testing.md`

### Project Evidence

- `_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md`
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/epics.md`
- `_bmad-output/planning-artifacts/implementation-readiness-report-2026-07-12.md`
- `_bmad-output/planning-artifacts/contracts/workflow-commander/README.md`
- `_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/workflow-provider-binding.schema.json`
- `_bmad-output/planning-artifacts/contracts/workflow-commander/examples/providers/archon/bindings/status-valid.json`
- `hermes_cli/projects_db.py`
- `hermes_cli/sqlite_util.py`
- `tests/hermes_cli/test_projects_db.py`
- `tests/hermes_cli/test_kanban_db_init.py`
- `tests/stress/test_atypical_scenarios.py`

---

**Generated by:** BMad TEA Agent — Master Test Architect  
**Workflow:** `bmad-testarch-test-design`
