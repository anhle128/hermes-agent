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
lastSaved: '2026-07-16'
inputDocuments:
  - '_bmad-output/implementation-artifacts/2-1b-validate-project-binding-safety-and-conflicts.md'
  - '_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md'
  - '_bmad-output/test-artifacts/test-design-epic-2.1a.md'
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics.md'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/README.md'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/operational-diagnostic.schema.json'
  - '_bmad-output/project-context.md'
  - 'hermes_project_work/bindings.py'
  - 'tests/project_work/test_bindings.py'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/risk-governance.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/probability-impact.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/test-levels-framework.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/test-priorities-matrix.md'
  - '.agents/skills/bmad-testarch-test-design/resources/knowledge/nfr-criteria.md'
---

# Test Design: Story 2.1b - Validate Project Binding Safety And Conflicts

**Date:** 2026-07-16
**Author:** Kevin
**Mode:** Epic-Level, scoped to Story 2.1b
**Status:** Draft - ready for implementation planning with explicit scope waivers

## Executive Summary

This plan covers the Project Binding validation slice: cwd safety, BMAD reference safety, non-raising re-validation for stored GitHub/provider metadata, conflict preview, conflict-category mapping, validation-state computation, and structured actionable diagnostics.

The implementation target is `hermes_project_work/bindings.py`; the test target is the existing `tests/project_work/test_bindings.py` file. The dominant test level is Python integration with real SQLite connections and real `tmp_path` filesystem state, matching Story 2.1a's existing patterns.

| Summary | Value |
| --- | --- |
| Risks | 16 total; 12 high priority with score >= 6 |
| P0 scenarios | 20 conceptual scenarios |
| P1 scenarios | 30 conceptual scenarios |
| P2/P3 scenarios | 0 planned; lower-risk concerns are covered by P1 regression/static checks or waived |
| Primary level | Python integration with real SQLite + filesystem; focused unit tests for private validation helpers |
| Estimated effort | ~36-66 hours, about 1-2 engineering weeks |
| Gate posture | Coverage is complete only if every P0/P1 scenario is implemented or the matching waiver is explicitly accepted |

## Not in Scope and Waivers

These waivers are not blank checks. Each one has an owner, residual risk, and trigger that reopens test design when the deferred behavior enters scope.

| Waiver | Reason | Owner | Residual risk | Follow-up trigger |
| --- | --- | --- | --- | --- |
| W-01 Actual activation command / public authorization | Story 2.1b provides `validate_binding()` and `preview_binding_conflicts()` only. The story explicitly says not to add `activate_binding()` or `enable_binding()`. | Owner of Story 2.1c/2.3 or first public command/API/tool caller | A future caller could start workflow actions without auth or without checking validation first. | Any command, API route, model tool, gateway action, or workflow action calls Project Binding validation. Add authorized, unauthorized, wrong-profile, and no-action-started tests. |
| W-02 Durable lifecycle state | `enabled`, persisted `validation_state`, update, disable, repair, re-enable, and audit history belong to Story 2.1c. | Story 2.1c owner | Validation may be recomputed correctly but not persisted or audited until 2.1c. | Any durable lifecycle column, status command, repair command, or audit record is added. |
| W-03 BMAD mount mutation | Mutating `skills.external_dirs`, mounting, reload, wrong-project mount diagnostics, and mounted skill discovery belong to Story 2.2. | Story 2.2 owner | A valid `bmad_skill_dir` path is not proof that BMAD skills are mounted or usable. | Any code mutates skill directories, reloads the skill index, or invokes BMAD through the stored reference. |
| W-04 Provider lifecycle / liveness | Archon registration, status, stale/disabled/rotated states, provider command I/O, and provider-side conflict diagnosis belong to Story 3.2 and later provider stories. | Story 3.2/provider-integration owner | Stored provider metadata can be structurally valid but operationally stale or missing. | Any provider adapter inspects, registers, refreshes, rotates, disables, or classifies provider binding health. |
| W-05 Workflow action cwd enforcement | Actually running BMAD/provider actions from the Bound Project Cwd belongs to Story 2.3. This story only produces the safety result future callers must gate on. | Story 2.3 owner | Validation can report unsafe while a future action path forgets to call it. | Any workflow execution path is introduced. Add P0 tests proving unsafe validation prevents process/subprocess/action start. |
| W-06 Durable OperationalDiagnostic persistence | Story 2.1b returns plain diagnostic dicts. Stable diagnostic IDs, severity, redaction history, and persistence belong to Story 5.3a. | Story 5.3a owner | Plain diagnostics may not yet satisfy the full operational-diagnostic schema. | Any diagnostic history/persistence/query feature is added. |
| W-07 External Archon producer evidence | This story validates local stored shape and exact vocabulary only; it does not consume live Archon output. | Provider-integration owner | Local fixtures do not prove real Archon producer compatibility. | Before any provider-dependent consumer story is marked done. |
| W-08 Async events, out-of-order delivery, timeout, and cancellation | The planned APIs are synchronous local functions with no queue, event timestamp, retry loop, timeout parameter, or cancellation token. | First async/event-driven binding operation owner | Later orchestration could mishandle stale events, duplicates, cancellation, or timeouts. | Add event ingestion, background validation, retries, cancellation, or timestamped binding commands. |
| W-09 Performance/scalability SLO | No product threshold exists for binding count, validation latency, or conflict-preview throughput. | Product owner + operations | Large stores could regress without a measurable gate. | An SLO, scale envelope, production contention signal, or benchmark requirement is approved. |
| W-10 Physical path alias equivalence | Story 2.1a stores normalized text paths; Story 2.1b checks current path safety. Physical identity via symlink/case-folding is not specified. | Architect + platform owner | The same repository may be reachable through aliases on some platforms. | Architecture chooses `realpath`/case-folding semantics or CI exposes alias collision misses. |
| W-11 Non-empty existing-binding conflict list | Current schema has hard unique indexes, so two persisted rows in one profile cannot collide through supported writes. Non-empty conflicts are reachable through `preview_binding_conflicts()`. | Story 2.1c update-path owner | A future update path or damaged DB could need the existing-binding conflict scan. | Any update path bypasses create-time uniqueness checks, or schema/index repair behavior changes. |

## Risk Assessment

Probability and impact use the TEA 1-3 scale. Score 9 is P0. Score 6-8 is P1. Lower scores can still be promoted when failure would break core behavior, security, data integrity, compatibility, or cross-process contract behavior.

### High-Priority Risks

| ID | Cat. | Risk | P | I | Score | Priority | Mitigation / planned evidence | Owner | Timeline |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| R-001 | SEC/DATA/OPS | Invalid cwd can be treated as safe, allowing future automation to run from a missing, non-directory, root, Hermes-home, or non-git path. | 3 | 3 | 9 | P0 | Unit cwd reasons plus `validate_binding()` unsafe diagnostics for missing/non-git/stale paths. | Dev + QA | Before merge |
| R-002 | SEC/DATA | Allowed-root policy order or Hermes-home/root denylist can be implemented incorrectly. | 2 | 3 | 6 | P1 | Test first-failure ordering, filesystem root, exact Hermes home, and nested Hermes home cases. | Dev + Security reviewer | Before merge |
| R-003 | TECH/DATA | Git repository detection can drift from project convention or shell out in a platform-fragile way. | 2 | 3 | 6 | P1 | Assert `.git` directory absence maps to `cwd_is_not_a_git_repository`; code review forbids `git rev-parse`. | Dev | Before merge |
| R-004 | TECH/OPS | Missing or invalid BMAD skill directory can raise, pass silently, or be mistaken for mount validation. | 2 | 3 | 6 | P1 | Unit BMAD reference checks plus end-to-end invalid BMAD diagnostic. | Dev + QA | Before merge |
| R-005 | DATA/TECH | Malformed stored `github_reference` or `provider_metadata` can escape as `ValueError`/`TypeError` instead of a structured diagnostic. | 3 | 3 | 9 | P0 | Raw-row malformed JSON/non-dict/identity-shape tests prove no exception escapes and only the relevant check is invalid. | Dev | Before merge |
| R-006 | DATA | Conflict preview can miss dimensions, report wrong categories, mutate rows, or hide ambiguity. | 3 | 3 | 9 | P0 | One preview test per dimension, all-dimensions aggregation, repeated preview, row-count invariants. | Dev + QA | Before merge |
| R-007 | DATA | Existing-binding conflict scan can report self as conflict or hide sibling collisions if exclusion is post-filtered. | 2 | 3 | 6 | P1 | Validate self-exclusion invariant and helper-level `exclude_binding_id` behavior. | Dev | Before merge |
| R-008 | COMPAT/OPS | Diagnostic vocabulary can drift from the agreed local categories or future operational-diagnostic enum strings. | 2 | 3 | 6 | P1 | Contract tests for `next_action_owner`, `recovery_option`, conflict categories, and nonempty messages. | Dev + QA | Before merge |
| R-009 | DATA/TECH | `validation_state` precedence or `safe` computation can disagree with diagnostics/checks. | 2 | 3 | 6 | P1 | Multi-failure precedence and safe-iff-valid tests. | Dev | Before merge |
| R-010 | TECH/COMPAT | Implementation can scope-creep into lifecycle columns, activation, BMAD mounting, provider liveness, CLI/tool wiring, or new runtime infra. | 2 | 3 | 6 | P1 | Regression/static checks plus W-01 through W-06. | Dev + reviewer | Before merge |
| R-012 | TECH/DATA | Mock-only tests can miss real SQLite, schema, filesystem, malformed row, and path behavior. | 2 | 3 | 6 | P1 | All integration scenarios use real `sqlite3.Connection`, real DB files, and `tmp_path`. | QA + Dev | Before merge |
| R-013 | DATA/OPS | Validation can rely on create-time state and miss stale filesystem changes after a binding is persisted. | 2 | 3 | 6 | P1 | Delete cwd, remove `.git`, and delete BMAD dir after create, then revalidate. | Dev + QA | Before merge |
| R-014 | DATA | Preview conflict scoping/normalization can disagree with `create_binding()`. | 2 | 3 | 6 | P1 | Preview tests for path normalization, GitHub canonical key, profile scoping, and different-profile non-conflicts. | Dev | Before merge |

### Medium and Low Risks

| ID | Cat. | Risk | P | I | Score | Priority | Mitigation / disposition | Owner |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| R-011 | TECH | Wrapper functions might duplicate `_validate_github_reference()` or `_validate_provider_identity()` logic and drift later. | 2 | 2 | 4 | P2 | Unit tests monkeypatch/sentinel the underlying validators where practical; code review confirms wrap-not-copy. | Dev |
| R-015 | TECH | Unknown binding id can be misclassified as a validation outcome instead of caller/programmer error. | 2 | 2 | 4 | P2 | `validate_binding()` unknown id raises `ValueError`; no row mutation. | Dev |
| R-016 | PERF/OPS | Validation performance is unknown at large binding counts. | 1 | 2 | 2 | P3 | W-09; do not invent an SLO. | Product + operations |

## Reviewer Concern Disposition

Every known concern from the story notes, referenced predecessor story, and contract guidance is treated as evidence. Concerns classified as explicit non-risks still carry P/I scoring and a waiver where behavior is deferred.

| Concern | Classification and rationale | P | I | Score | Scenario or waiver |
| --- | --- | ---: | ---: | ---: | --- |
| AC1 uses "activation" wording, but no activation command exists here. | Explicit non-risk for this story; adding activation would violate scope. | 1 | 1 | 1 | W-01, W-05 |
| Do not add `enabled`, durable `validation_state`, lifecycle, or audit columns. | Risk if ignored; breaks Story 2.1c contract ownership. | 2 | 3 | 6 | R-010; 2.1B-REG-001; W-02 |
| Do not mount BMAD skills or touch `skills.external_dirs`. | Explicit non-risk; Story 2.2 owns it. | 1 | 2 | 2 | W-03; 2.1B-REG-003 |
| Do not implement provider registration/liveness/status. | Explicit non-risk; Story 3.2 owns it. | 1 | 2 | 2 | W-04 |
| Cwd safety checks must fail in documented order. | Risk; wrong ordering can return misleading diagnostics. | 2 | 3 | 6 | R-001/R-002; 2.1B-UNIT-001 through 005 |
| Deny filesystem root and Hermes home exact/nested cwd. | Risk; self-modifying automation can corrupt profile data. | 2 | 3 | 6 | R-002; 2.1B-UNIT-003, 004 |
| Use `.git` directory convention, not shelling out to Git. | Risk; convention drift and platform fragility. | 2 | 3 | 6 | R-003; 2.1B-UNIT-005, 2.1B-INT-002, 028 |
| `_check_cwd_safety` assumes stored absolute normalized input; do not re-normalize inside it. | Risk; hidden normalization can mask bad stored data or diverge from create path. | 2 | 3 | 6 | R-014; 2.1B-REG-002/code review |
| Wrap existing GitHub/provider validators; do not duplicate logic. | Medium risk; duplicate logic drifts. | 2 | 2 | 4 | R-011; 2.1B-UNIT-011 through 014 |
| `validate_binding()` must not let `_binding_from_row()` raise before diagnostics. | P0 risk; malformed persisted rows must return diagnostics. | 3 | 3 | 9 | R-005; 2.1B-INT-004 through 007, 020, 030 |
| Malformed JSON/non-dict should invalidate only that check and continue assembling result. | P0 risk; partial diagnostics must remain actionable. | 3 | 3 | 9 | R-005; 2.1B-INT-020 |
| Conflict preview must be read-only. | P0 risk; preview creating rows corrupts data. | 3 | 3 | 9 | R-006; 2.1B-INT-008 through 012, 021, 026 |
| Conflict categories must map exact dimensions to exact local category strings. | P0/P1 risk; wrong categories break callers. | 3 | 3 | 9 | R-006/R-008; 2.1B-INT-008 through 012; 2.1B-CONTRACT-001 |
| `exclude_binding_id` must be applied in SQL, not by post-filtering self hits. | P1 risk; future damaged/update paths can hide sibling collisions. | 2 | 3 | 6 | R-007; 2.1B-INT-014 |
| Persisted conflicts are impossible through supported writes due hard unique indexes. | Explicit non-risk for non-empty `validate_binding().conflicts` today. | 1 | 2 | 2 | W-11; 2.1B-INT-013 validates invariant; preview scenarios cover reachable conflicts |
| Use exact `next_action_owner` and `recovery_option` strings. | P1 compatibility risk. | 2 | 3 | 6 | R-008; 2.1B-CONTRACT-001, 2.1B-INT-031 |
| Do not conflate local diagnostic category strings with schema coarse `category`. | P1 compatibility risk. | 2 | 3 | 6 | R-008; 2.1B-CONTRACT-001; W-06 for durable schema |
| Validation-state precedence must be deterministic. | P1 data/contract risk. | 2 | 3 | 6 | R-009; 2.1B-INT-013 |
| `safe` must be true iff every check is valid and conflicts are empty. | P1 data/contract risk. | 2 | 3 | 6 | R-009; 2.1B-INT-014 |
| Unknown binding id raises `ValueError` only. | Medium caller-contract risk. | 2 | 2 | 4 | R-015; 2.1B-INT-017 |
| Keep create path fail-fast behavior unchanged. | P1 regression risk; create and validate have different contracts. | 2 | 3 | 6 | R-010; 2.1B-REG-002 |
| Tests must stay in `tests/project_work/test_bindings.py` and use real SQLite/tmp paths. | P1 evidence risk. | 2 | 3 | 6 | R-012; 2.1B-REG-004; all INT scenarios |
| Do not add CLI/tool/core wiring or new runtime infrastructure. | P1 scope/compat risk if ignored. | 2 | 3 | 6 | R-010; 2.1B-REG-003; W-01 |
| Durable operational diagnostics are future work. | Explicit non-risk here; story only returns plain dicts. | 1 | 2 | 2 | W-06 |
| Provider metadata with one-sided Controller Identity or metadata without identity must not crash validation. | P0 risk for malformed stored data. | 3 | 3 | 9 | R-005; 2.1B-UNIT-014, 2.1B-INT-007, 030 |

## NFR Planning

This is a planning view only. Final NFR PASS/CONCERNS/FAIL belongs to `nfr-assess` after implementation evidence exists.

| NFR | Requirement / threshold | Risk link | Planned validation | Evidence needed |
| --- | --- | --- | --- | --- |
| Security / safety | Workflow actions must not trust unsafe cwd values; Hermes home and filesystem root are unsafe. No public auth surface in this story. | R-001, R-002, W-01, W-05 | Unit cwd safety checks and `validate_binding()` unsafe results; future action-block tests in Story 2.3. | Focused pytest/JUnit output; later Story 2.3 action-gate evidence. |
| Data integrity | Validation must not mutate rows during preview, must not hide conflicts, and must not crash on malformed persisted data. | R-005, R-006, R-007, R-009, R-013, R-014 | Real SQLite row-count checks, raw-row malformed data updates, stale filesystem checks, conflict preview invariants. | Pytest output with row counts, diagnostic shape, and validation-state assertions. |
| Compatibility / contracts | Diagnostic local category and recovery strings must remain compatible with existing planning schema vocabulary. | R-008, R-010 | Contract/vocabulary assertions against exact strings; no new schema columns for 2.1b. | Pytest output; optional contract-validator output for the shared package. |
| Reliability | Revalidation must use current filesystem state, not create-time assumptions. | R-001, R-004, R-013 | Delete cwd, remove `.git`, and remove BMAD dir after create; validate again. | Pytest output from `tests/project_work/test_bindings.py`. |
| Maintainability | Reuse existing validators and uniqueness helpers; avoid duplicate logic and new files. | R-011, R-012 | Unit monkeypatch/sentinel tests where useful plus review/static checks. | Ruff output, focused test output, code-review checklist. |
| Performance / scalability | UNKNOWN. No binding-count or latency threshold exists. | R-016 | W-09; no benchmark required. | None until a threshold is approved. |

## Entry Criteria

- [ ] Story 2.1b artifact remains the source of scope and accepted waiver ownership.
- [ ] Story 2.1a Project Binding persistence tests are green before adding 2.1b tests.
- [ ] `hermes_project_work/bindings.py` remains the only implementation file unless a justified test helper is needed.
- [ ] New tests are added to `tests/project_work/test_bindings.py`.
- [ ] Test setup uses real SQLite connections and real filesystem state under `tmp_path`.
- [ ] Any deferred activation/lifecycle/mount/provider behavior references the matching waiver.

## Exit Criteria

- [ ] All P0 scenarios pass at 100%.
- [ ] All deterministic P1 scenarios pass at 100%; no quarantined race/FS diagnostic test counts as evidence.
- [ ] Every AC, high-risk item, and reviewer concern maps to a scenario or a waiver with owner, residual risk, and trigger.
- [ ] No escaped `ValueError`/`TypeError` occurs for malformed persisted GitHub/provider fields.
- [ ] No preview scenario creates a row or mutates existing rows.
- [ ] No new `enabled`/`validation_state` columns, activation command, BMAD mount mutation, provider liveness check, CLI command, model tool, or runtime dependency is introduced.
- [ ] Ruff and focused `scripts/run_tests.sh tests/project_work/test_bindings.py -q` pass.

## Test Coverage Plan

P0/P1/P2/P3 indicate risk priority, not execution timing. Run the focused suite in PRs while it remains under 15 minutes. Parameterized cases should be emitted as independent pytest nodes.

### P0 - Blocking Safety, Data, and Contract Cases

| Test ID | Atomic scenario | Level | Trace | Owner |
| --- | --- | --- | --- | --- |
| 2.1B-UNIT-001 | `_check_cwd_safety()` returns invalid `cwd_does_not_exist` for a missing cwd. | Unit | AC1, R-001 | Dev/QA |
| 2.1B-UNIT-002 | `_check_cwd_safety()` returns invalid `cwd_is_not_a_directory` for an existing file. | Unit | AC1, R-001 | Dev/QA |
| 2.1B-UNIT-003 | `_check_cwd_safety()` returns invalid `cwd_is_filesystem_root` for a filesystem root-like path. | Unit | AC1, R-001/R-002 | Dev/QA |
| 2.1B-UNIT-004 | `_check_cwd_safety()` returns invalid `cwd_is_within_hermes_home` for exact and nested Hermes home paths. | Unit | AC1, R-001/R-002 | Dev/QA |
| 2.1B-UNIT-005 | `_check_cwd_safety()` returns invalid `cwd_is_not_a_git_repository` for an existing directory without `.git`. | Unit | AC3, R-001/R-003 | Dev/QA |
| 2.1B-INT-001 | `validate_binding()` on a binding whose cwd no longer exists returns `safe: False`, `validation_state: invalid_cwd`, and `invalid_cwd` diagnostic. | Integration | AC1, R-001/R-013 | Dev/QA |
| 2.1B-INT-002 | `validate_binding()` on an existing non-git cwd returns reason `cwd_is_not_a_git_repository` and does not raise. | Integration | AC3, R-001/R-003 | Dev/QA |
| 2.1B-INT-003 | Fully valid binding with `.git`, valid BMAD dir, valid GitHub ref, and valid provider metadata returns `validation_state: valid`, `safe: True`, no diagnostics, and empty conflicts. | Integration | AC6, R-009 | Dev/QA |
| 2.1B-INT-004 | Raw SQL malformed `github_reference` JSON returns `invalid_github_reference` diagnostic and no exception. | Integration | AC5, R-005 | Dev/QA |
| 2.1B-INT-005 | Raw SQL `github_reference` JSON that parses to a non-dict returns `invalid_github_reference` diagnostic and no exception. | Integration | AC5, R-005 | Dev/QA |
| 2.1B-INT-006 | Raw SQL malformed `provider_metadata` JSON returns `invalid_provider_metadata` diagnostic and no exception. | Integration | AC5, R-005 | Dev/QA |
| 2.1B-INT-007 | Raw SQL provider metadata/identity shape failures, including one-sided Controller Identity and metadata without full identity, return `invalid_provider_metadata` diagnostic and no exception. | Integration | AC5, R-005 | Dev/QA |
| 2.1B-INT-008 | `preview_binding_conflicts()` matching existing `bound_project_cwd` returns `cwd_conflict` and the existing binding id without creating a row. | Integration | AC2, AC7, R-006 | Dev/QA |
| 2.1B-INT-009 | `preview_binding_conflicts()` matching existing GitHub owner/repo returns `github_reference_conflict` and the existing binding id without creating a row. | Integration | AC2, AC7, R-006/R-014 | Dev/QA |
| 2.1B-INT-010 | `preview_binding_conflicts()` matching existing BMAD skill dir returns `bmad_mount_conflict` and the existing binding id without creating a row. | Integration | AC2, AC7, R-006 | Dev/QA |
| 2.1B-INT-011 | `preview_binding_conflicts()` matching existing provider/name identity returns `provider_identity_conflict` and the existing binding id without creating a row. | Integration | AC2, AC7, R-006 | Dev/QA |
| 2.1B-INT-012 | Candidate matching all four dimensions returns all four conflict categories, all linked to the existing binding id, and row count remains unchanged. | Integration | AC2, AC7, R-006 | Dev/QA |
| 2.1B-INT-013 | Multi-failure binding computes validation state in precedence order: `invalid_cwd` before BMAD, GitHub, provider metadata, conflict, and valid. | Integration | AC1, AC4, AC5, R-009 | Dev/QA |
| 2.1B-INT-014 | `safe` is true iff cwd/GitHub/provider/BMAD checks are valid or optional and conflicts are empty. | Integration | AC1, AC4, AC5, AC6, R-009 | Dev/QA |
| 2.1B-CONTRACT-001 | Each diagnostic uses exact local category strings, `next_action_owner: configuration`, and exact recovery option `repair_project_binding` or `update_project_binding`. | Contract integration | AC1, AC2, AC4, AC5, R-008 | Dev/QA |

### P1 - Core Validation, Stale Data, Scope, and Regression Cases

| Test ID | Atomic scenario | Level | Trace | Owner |
| --- | --- | --- | --- | --- |
| 2.1B-UNIT-006 | `_check_cwd_safety()` returns valid for an existing directory containing `.git`. | Unit | AC6, R-001 | Dev/QA |
| 2.1B-UNIT-007 | `_check_bmad_reference_safety(None)` returns `None`. | Unit | AC4, R-004 | Dev/QA |
| 2.1B-UNIT-008 | `_check_bmad_reference_safety()` returns invalid `bmad_skill_dir_does_not_exist` for a missing path. | Unit | AC4, R-004 | Dev/QA |
| 2.1B-UNIT-009 | `_check_bmad_reference_safety()` returns invalid `bmad_skill_dir_is_not_a_directory` for a file. | Unit | AC4, R-004 | Dev/QA |
| 2.1B-UNIT-010 | `_check_bmad_reference_safety()` returns valid for an existing directory. | Unit | AC4, AC6, R-004 | Dev/QA |
| 2.1B-UNIT-011 | `_check_github_reference_safety(None)` and a valid dict return valid results. | Unit | AC5, R-011 | Dev/QA |
| 2.1B-UNIT-012 | `_check_github_reference_safety()` converts a validator-raised non-dict or malformed shape into invalid result without raising. | Unit | AC5, R-005/R-011 | Dev/QA |
| 2.1B-UNIT-013 | `_check_provider_metadata_safety()` returns valid for absent metadata/identity and valid complete identity/metadata. | Unit | AC5, R-011 | Dev/QA |
| 2.1B-UNIT-014 | `_check_provider_metadata_safety()` converts one-sided identity, metadata-without-identity, and non-dict metadata into invalid result without raising. | Unit | AC5, R-005/R-011 | Dev/QA |
| 2.1B-INT-015 | `validate_binding()` never reports a binding as conflicting with itself. | Integration | AC2, AC6, R-007 | Dev/QA |
| 2.1B-INT-016 | `_check_uniqueness_dimensions(..., exclude_binding_id=...)` excludes the requested id in SQL and still finds a different matching sibling when one exists. | Integration | AC2, R-007 | Dev/QA |
| 2.1B-INT-017 | Unknown `binding_id` causes `validate_binding()` to raise `ValueError` and does not mutate rows. | Integration | R-015 | Dev/QA |
| 2.1B-INT-018 | `validate_binding()` with missing stored `bmad_skill_dir` path returns `invalid_bmad_reference` diagnostic and no exception. | Integration | AC4, R-004 | Dev/QA |
| 2.1B-INT-019 | `validate_binding()` with existing BMAD directory and otherwise valid binding remains safe. | Integration | AC4, AC6, R-004 | Dev/QA |
| 2.1B-INT-020 | When one JSON field is malformed, `validate_binding()` continues assembling cwd, BMAD, the other metadata check, conflicts, and diagnostics. | Integration | AC5, R-005 | Dev/QA |
| 2.1B-INT-021 | Non-conflicting preview returns `[]` and row count remains unchanged. | Integration | AC7, R-006 | Dev/QA |
| 2.1B-INT-022 | Preview normalizes candidate cwd/BMAD paths and canonicalizes GitHub owner/repo exactly like `create_binding()`. | Integration | AC7, R-014 | Dev/QA |
| 2.1B-INT-023 | Preview with invalid provider candidate fails before SQL mutation using existing provider validator behavior. | Integration | AC7, R-010/R-014 | Dev/QA |
| 2.1B-INT-024 | Preview with `profile=None` uses active/default profile resolution and reports only same-profile conflicts. | Integration | AC2, AC7, R-014 | Dev/QA |
| 2.1B-INT-025 | Same cwd/GitHub/BMAD/provider values in a different profile do not conflict. | Integration | AC2, AC7, R-014 | Dev/QA |
| 2.1B-INT-026 | Repeating the same preview action returns the same conflicts and still creates no row. | Integration | AC7, R-006 | Dev/QA |
| 2.1B-INT-027 | Binding created with valid cwd becomes unsafe after the cwd directory is deleted. | Integration | AC1, R-013 | Dev/QA |
| 2.1B-INT-028 | Binding created with valid cwd becomes unsafe after `.git` is removed. | Integration | AC3, R-013 | Dev/QA |
| 2.1B-INT-029 | Binding created with valid BMAD dir becomes unsafe after the BMAD directory is deleted. | Integration | AC4, R-013 | Dev/QA |
| 2.1B-INT-030 | Raw SQL one-sided provider identity columns return invalid provider metadata diagnostic, not an exception. | Integration | AC5, R-005 | Dev/QA |
| 2.1B-INT-031 | Every diagnostic message is nonempty, actionable, and includes the affected local category. | Integration | AC1, AC2, AC4, AC5, R-008 | Dev/QA |
| 2.1B-REG-001 | Schema PRAGMA shows no new `enabled`, durable `validation_state`, or audit columns were added by Story 2.1b. | Regression/static | R-010, W-02 | Dev/QA |
| 2.1B-REG-002 | Existing `create_binding()` fail-fast tests for invalid GitHub/provider input still pass unchanged. | Regression | R-010/R-011 | Dev/QA |
| 2.1B-REG-003 | Code review/static search confirms no activation command, CLI/tool wiring, BMAD mount mutation, provider liveness, or new runtime dependency was introduced. | Regression/static | R-010, W-01, W-03, W-04, W-05 | Reviewer |
| 2.1B-REG-004 | Test implementation is colocated in `tests/project_work/test_bindings.py` and integration tests use real SQLite/filesystem state, not mock-only DB/path substitutes. | Regression/static | R-012 | Reviewer |

## Mandatory Traceability

### Acceptance Criteria

| AC | Atomic scenarios / waiver | Result |
| --- | --- | --- |
| AC1 invalid cwd/outside allowed roots rejects activation with structured diagnostic | 2.1B-UNIT-001 through 005; 2.1B-INT-001, 002, 013, 014, 027, 028; 2.1B-CONTRACT-001; W-01/W-05 for actual activation/action start | Covered for validation function; actual action block deferred to Story 2.3. |
| AC2 conflicts on profile/cwd/GitHub/BMAD/provider block ambiguous automation with references/categories | 2.1B-INT-008 through 016, 024, 025; 2.1B-CONTRACT-001; W-11 for non-empty persisted conflict in `validate_binding()` today | Covered through reachable preview path and self-exclusion invariant. |
| AC3 cwd exists but no `.git` is unsafe | 2.1B-UNIT-005; 2.1B-INT-002, 028 | Covered. |
| AC4 missing BMAD skill directory reports invalid BMAD diagnostic without exception | 2.1B-UNIT-007 through 010; 2.1B-INT-018, 019, 029; 2.1B-CONTRACT-001 | Covered. |
| AC5 malformed GitHub/provider metadata returns structured diagnostic instead of propagated exception | 2.1B-UNIT-011 through 014; 2.1B-INT-004 through 007, 020, 030; 2.1B-CONTRACT-001 | Covered. |
| AC6 fully valid, non-conflicting binding returns valid/safe/no diagnostics/empty conflicts | 2.1B-INT-003, 014, 015, 019; 2.1B-UNIT-006, 010 | Covered. |
| AC7 candidate preview returns each conflicting dimension category and existing id without creating a row | 2.1B-INT-008 through 012, 021 through 026 | Covered. |

### High-Risk Items

| Risk | Scenarios / waiver |
| --- | --- |
| R-001 | 2.1B-UNIT-001 through 005; 2.1B-INT-001, 002, 027, 028 |
| R-002 | 2.1B-UNIT-003, 004; 2.1B-REG-002/code review |
| R-003 | 2.1B-UNIT-005; 2.1B-INT-002, 028 |
| R-004 | 2.1B-UNIT-007 through 010; 2.1B-INT-018, 019, 029 |
| R-005 | 2.1B-UNIT-012, 014; 2.1B-INT-004 through 007, 020, 030 |
| R-006 | 2.1B-INT-008 through 012, 021, 026 |
| R-007 | 2.1B-INT-015, 016; W-11 for currently impossible persisted conflicts |
| R-008 | 2.1B-CONTRACT-001; 2.1B-INT-031 |
| R-009 | 2.1B-INT-003, 013, 014 |
| R-010 | 2.1B-REG-001 through 003; W-01 through W-06 |
| R-012 | 2.1B-REG-004; all INT scenarios use real SQLite/filesystem |
| R-013 | 2.1B-INT-027 through 029 |
| R-014 | 2.1B-INT-022, 024, 025 |

### Reviewer Concerns

| Reviewer concern | Scenario or waiver |
| --- | --- |
| No activation command in this story | W-01, W-05 |
| No durable lifecycle columns/status/audit | 2.1B-REG-001; W-02 |
| No BMAD mount mutation | 2.1B-REG-003; W-03 |
| No provider liveness/registration | 2.1B-REG-003; W-04 |
| Cwd safety failure order | 2.1B-UNIT-001 through 005 |
| Root/Hermes-home denylist | 2.1B-UNIT-003, 004 |
| `.git` directory convention | 2.1B-UNIT-005; 2.1B-INT-002, 028 |
| Stored-normalized cwd assumption | 2.1B-REG-002/code review; 2.1B-INT-022 covers create/preview normalization boundary |
| Wrap existing validators | 2.1B-UNIT-011 through 014; 2.1B-REG-002 |
| Raw-row validation path avoids `_binding_from_row()` exception | 2.1B-INT-004 through 007, 020, 030 |
| Malformed field invalidates only that check and continues | 2.1B-INT-020 |
| Preview is read-only | 2.1B-INT-008 through 012, 021, 026 |
| Exact conflict categories | 2.1B-INT-008 through 012; 2.1B-CONTRACT-001 |
| SQL self-exclusion, no post-filter-only logic | 2.1B-INT-015, 016 |
| Do not force persisted duplicate rows | W-11; 2.1B-INT-015 |
| Exact diagnostic owner/recovery strings | 2.1B-CONTRACT-001; 2.1B-INT-031 |
| Local diagnostic categories not schema categories | 2.1B-CONTRACT-001; W-06 |
| Validation-state precedence | 2.1B-INT-013 |
| Safe iff valid | 2.1B-INT-014 |
| Unknown id raises `ValueError` | 2.1B-INT-017 |
| Create path remains fail-fast | 2.1B-REG-002 |
| Tests colocated and real SQLite/tmp path | 2.1B-REG-004; all INT scenarios |
| No CLI/tool/core wiring or new infra | 2.1B-REG-003; W-01 |
| Durable operational diagnostics deferred | W-06; 2.1B-CONTRACT-001 covers local vocabulary only |
| Provider metadata one-sided identity handling | 2.1B-UNIT-014; 2.1B-INT-007, 030 |

### Edge-Class Audit

| Required class | Coverage |
| --- | --- |
| Happy path | 2.1B-INT-003, 019, 021, 025; 2.1B-UNIT-006, 010, 011, 013 |
| Negative path | 2.1B-UNIT-001 through 005, 008, 009, 012, 014; 2.1B-INT-001, 002, 004 through 012, 018 |
| Boundary cases | Filesystem root, Hermes home exact/nested, optional BMAD `None`, profile scoping, same identity in different profiles |
| Malformed input/data | 2.1B-UNIT-012, 014; 2.1B-INT-004 through 007, 020, 030 |
| Stale data | 2.1B-INT-027 through 029 |
| Duplicate actions | 2.1B-INT-026 |
| Out-of-order events | W-08 |
| Partial failure | 2.1B-INT-020, 023, 030 |
| Dependency failure | Missing/deleted cwd and BMAD filesystem dependencies: 2.1B-INT-001, 018, 027 through 029 |
| Timeout | W-08; no timeout-bearing API in this story |
| Cancellation | W-08; no cancellation-bearing API in this story |
| Concurrency/race | Existing Story 2.1a unique-index race coverage remains regression evidence; Story 2.1b reachable conflict path is read-only preview. W-11 reopens if update paths add races. |
| Rollback | Preview row-count invariants: 2.1B-INT-008 through 012, 021, 026; invalid preview before SQL: 2.1B-INT-023 |
| Permission/auth | W-01; no public caller in this story |
| Regression | 2.1B-REG-001 through 004 plus existing Story 2.1a `create_binding()` tests |

## Execution Strategy

- **PR:** Run `scripts/run_tests.sh tests/project_work/test_bindings.py -q` and Ruff on touched files. Include all deterministic P0/P1 validation scenarios because the focused file should remain below 15 minutes.
- **Nightly:** Run the focused project-work tests with the broader SQLite/profile/concurrency regression cluster. Repeat Story 2.1a cross-process race tests if this story touches uniqueness helper behavior.
- **Weekly:** Run the full isolated Python suite. No performance benchmark is required until W-09 has a measurable threshold.

## Resource Estimates

| Priority | Estimate |
| --- | --- |
| P0 safety, malformed-data, conflict, and diagnostic contract automation | ~16-28 hours |
| P1 helper, stale-data, profile/normalization, scope, and regression automation | ~18-34 hours |
| Review/static checks and documentation polish | ~2-4 hours |
| Performance/exploratory work | ~0 hours until W-09 is triggered |
| **Total** | **~36-66 hours, about 5-9 engineering days** |

## Quality Gate Criteria

- **P0 pass rate:** 100%, no exceptions.
- **P1 pass rate:** 100% for deterministic data-integrity, compatibility, and scope-regression tests; stricter than generic 95% because this story is a safety gate for later workflow execution.
- **Traceability:** 100% of acceptance criteria, high risks, and reviewer concerns must map to a scenario or waiver.
- **Coverage target:** >=80% for new/changed Project Binding validation code if coverage is collected; behavior traceability is the authoritative gate.
- **NFR evidence:** Security, data integrity, compatibility, reliability, and maintainability evidence sources identified above; final NFR decision deferred to `nfr-assess`.
- **No scope creep:** No new activation command, durable lifecycle column, BMAD mount mutation, provider liveness check, CLI/tool/core wiring, runtime service, or new dependency.
- **No false confidence:** P0/P1 edge cases are explicit; no P0/P1 behavior is accepted by implication only.
