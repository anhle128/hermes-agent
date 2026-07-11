---
project: hermes-agent
workflow: bmad-check-implementation-readiness
invocation: hermes-workflow
date: 2026-07-12
status: NOT READY
issueCounts:
  critical: 1
  major: 1
  minor: 1
  warnings: 0
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
selectedFiles:
  prd: _bmad-output/planning-artifacts/prd.md
  architecture: _bmad-output/planning-artifacts/architecture.md
  epics: _bmad-output/planning-artifacts/epics.md
  ux: _bmad-output/planning-artifacts/ux-headless-interaction-contract.md
duplicateFindings: []
missingFindings: []
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-12
**Project:** hermes-agent

## Document Discovery

### PRD Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/prd.md` (16,253 bytes, modified 2026-07-12 06:13:53)

**Sharded Documents:**
- None found

**Selected for assessment:** `_bmad-output/planning-artifacts/prd.md`

### Architecture Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/architecture.md` (11,708 bytes, modified 2026-07-12 06:14:16)

**Sharded Documents:**
- None found

**Selected for assessment:** `_bmad-output/planning-artifacts/architecture.md`

### Epics & Stories Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/epics.md` (66,972 bytes, modified 2026-07-12 06:14:59)

**Sharded Documents:**
- None found

**Selected for assessment:** `_bmad-output/planning-artifacts/epics.md`

### UX Design Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md` (3,533 bytes, modified 2026-07-12 06:15:33)

**Sharded Documents:**
- None found

**Selected for assessment:** `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md`

### Discovery Issues

- None.

## PRD Analysis

### Functional Requirements

FR-1: Hermes can create, view, update, disable, and validate a Project Binding with profile identity, Bound Project Cwd, GitHub reference, BMAD skill directory reference, workflow provider binding metadata, and display name. It rejects invalid cwd values, returns the active binding before BMAD/provider actions, persists enough metadata to reconstruct status after restart, and reports provider binding status as missing, valid, stale, disabled, rotated, or conflicting when available.

FR-2: Hermes can add the bound project's BMAD skill directory to the selected profile's `skills.external_dirs`, reload that profile's skill index, record the source directory, avoid using global skills as the primary BMAD mount for multi-project control, and detect missing or wrong-project BMAD mounts.

FR-3: Hermes runs BMAD and provider actions for a Project Binding from the Bound Project Cwd unless explicitly stated otherwise. BMAD artifacts created through Hermes land under the bound project's configured output location. Hermes blocks actions without a valid cwd, records the cwd used for each workflow action, and does not infer cwd from skill visibility alone.

FR-4: Hermes can invoke selected BMAD planning workflows for brainstorming, product brief, PRD, architecture, epics, stories, sprint status, create-story, and dev-story preparation from the Bound Project Cwd. It presents BMAD as a behind-the-scenes workflow engine, records produced artifact paths, preserves Project Binding context on failure, and continues orchestration from generated BMAD artifacts.

FR-5: Hermes can read `sprint-status.yaml` from the Bound Project Cwd and idempotently create or update Project Work Items for BMAD epics and stories. Re-runs update existing items instead of duplicating them. Hermes stores BMAD artifact references and observed planning status, and does not treat `sprint-status.yaml` as the runtime queue after materialization.

FR-6: Hermes persists operational backlog, selected story, phase metadata, workflow references, human gate metadata, and next action as operational project-work state. It exposes that state through structured command, agent, or API results while keeping canonical Kanban lifecycle values unchanged: `triage`, `todo`, `ready`, `running`, `blocked`, `done`, and `archived`.

FR-7: Hermes can register or inspect provider-side workflow bindings through generic `provider` and `name` vocabulary, detect disagreement between Project Binding and provider binding metadata, and surface missing, stale, disabled, rotated, and conflicting provider binding states as actionable diagnostics. Archon owns producer-side provider binding persistence and status production.

FR-8: Hermes can start, inspect, approve, reject, resume, retry, and cancel provider workflow runs through the adapter selected by the Project Binding. For `archon`, Hermes consumes parseable CLI JSON, captures stdout, stderr, exit code, cwd when applicable, timeout, correlation id, and parsed result, and fails closed on malformed JSON, incompatible schema version, timeout, unexpected exit code, or unexpected state. Hermes does not use provider HTTP APIs for the `archon` state-changing control path.

FR-9: Hermes receives signed workflow provider events on `/p/{profile}/webhooks/workflow-events/{provider}` and mutates project work only after schema, binding, replay, idempotency, provider, profile, and authorization validation pass. Hermes rejects unknown Project Binding, wrong profile, wrong codebase, stale timestamp, duplicate event id, invalid signature, unsupported provider, and schema failure before mutation, stores accepted event ids and idempotency keys, and maps completion, failure, approval-request, and artifact events only to the intended Project Work Item or Phase Task.

FR-10: Hermes can return structured provider event-delivery status identifying healthy, delayed, failed, duplicated, terminal failure, or reconciliation-pending state. It exposes this evidence through Story Status History and diagnostics and does not block provider workflow execution solely because event notification failed. Archon owns producer-side outbox and delivery-health status for provider `archon`.

FR-11: Hermes materializes each selected BMAD story as a single Phase Task linked to one Project Work Item and shared Story Status History evidence. Repeated materialization must not duplicate Phase Tasks.

FR-12: Hermes can run the configured combined story workflow for a selected BMAD story, record the provider workflow run reference on the Phase Task, and allow the workflow to run story creation through review without a Hermes-side pause between phases.

FR-13: Hermes blocks the Phase Task for a Done Verification Gate after provider completion evidence arrives. Human approval completes the Phase Task. Human rejection routes to rerun, resume, retry, or recovery without marking the story complete.

FR-14: Hermes can publish or return structured gate evidence, accept approval or rejection through an authorized command or agent interaction, persist the decision, and send the matching provider command when required. Each gate decision records actor, timestamp, gate kind, decision, reason when present, and evidence references. Hermes does not auto-continue past a HILT Gate unless an explicit persisted policy later permits it.

FR-15: Hermes can return one source-labeled Story Status History containing BMAD milestones, Project Work Item state, Phase Task state, provider run references, workflow events, GitHub PR references, HILT Gate decisions, provenance, and next action. The history distinguishes BMAD planning lifecycle from Hermes runtime lifecycle and GitHub PR merge state from Done Verification state.

FR-16: Hermes compares BMAD artifact state, provider workflow state, GitHub PR state, Hermes Project Work Item state, and HILT Gate state to detect drift. It may repair deterministic projection drift, but must not auto-approve HILT Gates or mark stories complete when evidence conflicts.

FR-17: Hermes surfaces binding conflicts, cwd problems, missing BMAD artifacts, unsupported sprint status, provider command contract gaps, event delivery failures, duplicate workflow events, outbox backlog, stale PR references, and unresolved gates. Diagnostics distinguish responsible domains, include recovery guidance, and redact secrets.

Total FRs: 17

### Non-Functional Requirements

NFR-1: Workflow events are delivery acceleration, not the sole source of truth.
NFR-2: Reconciliation handles event loss, duplicate delivery, gateway downtime, provider command failure, and manual PR merge.
NFR-3: Materialization is idempotent.
NFR-4: Gate decisions are replay-safe and auditable.
NFR-5: Event ingress fails closed on signature, schema, replay, binding, provider, profile, idempotency, or authorization failure.
NFR-6: Workflow event secrets are scoped to the correct profile.
NFR-7: Workflow actions cannot run outside the selected Bound Project Cwd.
NFR-8: Secrets are redacted from command logs, event logs, diagnostics, and status-history results.
NFR-9: Workflow commands, workflow events, reconciliation actions, gate decisions, and user-visible state transitions are persisted.
NFR-10: Story Status History explains why a story changed state.
NFR-11: Project-work changes retain source provenance.
NFR-12: Next actions use human-facing workflow language.
NFR-13: Done Verification approval remains separate from GitHub PR merge state.
NFR-14: Blocking issues return recovery options instead of raw stack traces alone.
NFR-15: Dependency records and handoff validation preserve bounded ownership between Hermes, BMAD, workflow providers, GitHub, and parent shared contracts.
NFR-16: Provider integration surfaces remain generic.
NFR-17: Isolated local handoffs are complete enough for subproject implementation agents.

Total NFRs: 17

### Additional Requirements

- v1 is headless and excludes a dedicated dashboard, graphical Kanban board, gate screen, timeline screen, desktop view, web application, marketing surface, or dedicated graphical frontend.
- Hermes owns Project Binding, BMAD mount, Bound Project Cwd enforcement, BMAD invocation, materialization, Project Work Items, Phase Tasks, HILT Gates, provider adapter consumption, workflow event ingress, Story Status History, reconciliation, diagnostics, and headless validation guidance.
- Archon is the first workflow provider and owns producer-side workflow execution, run state, provider binding, provider command JSON, event outbox, delivery status, and signed event production.
- Required local contract schemas and example fixture families must exist under `contracts/workflow-commander/` and pass compatibility tests before contract-gated downstream stories can complete.
- Candidate validation commands are `uv sync --extra dev`, `uv run pytest`, and `uv run ruff check .`.

### PRD Completeness Assessment

The PRD is clear about product boundary, ownership boundary, provider boundary, functional requirements, non-functional requirements, and downstream contract readiness. It is suitable for traceability validation against epics.

## Epic Coverage Validation

### Epic FR Coverage Extracted

- FR-1: Covered by Epic 2, Stories 2.1a, 2.1b, and 2.1c.
- FR-2: Covered by Epic 2, Story 2.2.
- FR-3: Covered by Epic 2, Story 2.3.
- FR-4: Covered by Epic 2, Story 2.4.
- FR-5: Covered by Epic 2, Story 2.5.
- FR-6: Covered by Epic 2, Story 2.6.
- FR-7: Covered by Epic 3, Story 3.2.
- FR-8: Covered by Epic 3, Stories 3.4a, 3.4b, and 3.4c.
- FR-9: Covered by Epic 3, Stories 3.6a, 3.6b, 3.6c, 3.6d, and 3.6e.
- FR-10: Covered by Epic 3, Story 3.8.
- FR-11: Covered by Epic 2 Story 2.6 and Epic 3 Story 3.6c.
- FR-12: Covered by Epic 3 Stories 3.6c and 3.6e and Epic 4 Story 4.1.
- FR-13: Covered by Epic 3 Story 3.6d and Epic 4 Story 4.2.
- FR-14: Covered by Epic 3 Story 3.4b and Epic 4 Stories 4.1, 4.2, and 4.3.
- FR-15: Covered by Epic 5, Story 5.1.
- FR-16: Covered by Epic 5, Stories 5.2a, 5.2b, 5.2c, 5.2d, and 5.2e.
- FR-17: Covered by Epic 5, Stories 5.3a, 5.3b, and 5.3c.

Total FRs in epics: 17

### Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| --- | --- | --- | --- |
| FR-1 | Create and manage Project Bindings | Epic 2, Stories 2.1a-2.1c | Covered |
| FR-2 | Mount project-local BMAD skills | Epic 2, Story 2.2 | Covered |
| FR-3 | Enforce Bound Project Cwd | Epic 2, Story 2.3 | Covered |
| FR-4 | Invoke BMAD planning workflows | Epic 2, Story 2.4 | Covered |
| FR-5 | Materialize sprint status into Project Work Items | Epic 2, Story 2.5 | Covered |
| FR-6 | Maintain Hermes-owned operational backlog | Epic 2, Story 2.6 | Covered |
| FR-7 | Consume generic workflow provider bindings | Epic 3, Story 3.2 | Covered |
| FR-8 | Control provider workflows through adapters | Epic 3, Stories 3.4a-3.4c | Covered |
| FR-9 | Receive typed workflow provider events | Epic 3, Stories 3.6a-3.6e | Covered |
| FR-10 | Return event delivery and outbox health | Epic 3, Story 3.8 | Covered |
| FR-11 | Create one Phase Task per BMAD story | Epic 2 Story 2.6; Epic 3 Story 3.6c | Covered |
| FR-12 | Run combined story workflow | Epic 3 Stories 3.6c and 3.6e; Epic 4 Story 4.1 | Covered |
| FR-13 | Gate Done Verification | Epic 3 Story 3.6d; Epic 4 Story 4.2 | Covered |
| FR-14 | Collect human decisions from Hermes | Epic 3 Story 3.4b; Epic 4 Stories 4.1-4.3 | Covered |
| FR-15 | Return unified Story Status History | Epic 5, Story 5.1 | Covered |
| FR-16 | Reconcile cross-system state | Epic 5, Stories 5.2a-5.2e | Covered |
| FR-17 | Provide operational diagnostics | Epic 5, Stories 5.3a-5.3c | Covered |

### Missing Requirements

No PRD FRs are missing from the epics document. No extra FR identifiers appear in epics outside PRD FR-1 through FR-17.

### Coverage Statistics

- Total PRD FRs: 17
- FRs covered in epics: 17
- Coverage percentage: 100%

## UX Alignment Assessment

### UX Document Status

Found: `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md`.

### Alignment Issues

No UX alignment issues were found. The UX document, PRD, and architecture all define Workflow Commander v1 as a headless operator experience delivered through Hermes commands, agent interactions, structured command/API results, durable records, Story Status History, diagnostics, and optional existing notification transports.

The UX contract's required response shapes are supported by architecture decisions and story coverage:

- Project Binding inspection maps to FR-1, AD-2, and Stories 2.1a-2.1c.
- BMAD workflow invocation maps to FR-3/FR-4, AD-4, and Stories 2.3-2.4.
- Provider workflow control maps to FR-7/FR-8, AD-3, and Stories 3.2 and 3.4a-3.4c.
- Done Verification Gate maps to FR-13/FR-14, the gate interaction/completion conventions, and Stories 4.2-4.3.
- Story Status History maps to FR-15, AD-5, and Story 5.1.
- Operational diagnostics map to FR-17 and Stories 5.3a-5.3c.

### Warnings

None. A dedicated graphical UX is explicitly out of scope for v1, and the headless UX artifact supplies validation expectations for commands, structured results, gates, Story Status History, diagnostics, and redaction.

## Epic Quality Review

### Epic Structure Validation

The epics are user-outcome oriented rather than technical milestones:

- Epic 2 lets Kevin bind a project, mount BMAD skills, run planning from the correct cwd, and materialize BMAD stories into Hermes project work.
- Epic 3 lets Kevin connect to workflow providers, control workflow runs, and inspect event/outbox health without opening the provider dashboard.
- Epic 4 lets Kevin run the combined story workflow, review Done Verification evidence, approve or reject, and route recovery.
- Epic 5 lets Kevin query Story Status History, understand drift, and resolve operational diagnostics.

The local handoff intentionally starts at Epic 2 because parent/shared-contract work owns earlier contract stories. This is documented in the epics frontmatter and the cross-project isolated handoff contract, so the numbering gap is not a quality defect.

### Story Structure Validation

- Story headings found: 30.
- Stories with `Requirements Covered`: 30.
- Stories with `Implementation Scope`: 30.
- Stories with `Acceptance Criteria`: 30.
- Acceptance criteria are generally testable and use Given/When/Then form.
- Error and failure paths are represented for binding conflicts, invalid cwd, mount failure, malformed provider JSON, schema mismatch, duplicate events, unresolved mappings, delayed delivery, rejected gates, redaction, diagnostics, and reconciliation conflicts.
- Database/entity creation is scoped to the story that first needs the data. The epics do not ask for all tables or models to be created upfront.
- Brownfield constraints are represented: the architecture keeps the existing Hermes runtime, uses ports/adapters, preserves Kanban lifecycle values, and avoids new runtime infrastructure or dedicated graphical frontend.

### Dependency Analysis

No forward dependency between Hermes-owned stories was found. Hermes-owned story dependencies point to earlier same-project stories, parent contract stories, or Archon producer stories. External parent/Archon dependencies are explicitly recorded with `Depends on`, `Contract needed`, `Blocking behavior`, and `Integration validation`.

The local contract package validation passed:

```text
Workflow Commander 1.3a/1.3b/1.3c contract validation passed
Validated 7 schemas
Validated 16 command examples
Validated 14 binding examples
Validated 7 delivery examples
Validated 6 generic event examples
Validated 7 provider event examples
Validated 9 callback rejection examples
Validated 6 materialization examples
Validated isolated local package without parent workspace traversal
```

### Critical Violations

1. **Implementation tracker is stale and does not match the current epics.**
   - Evidence: `_bmad-output/planning-artifacts/epics.md` defines 30 current Hermes-owned story headings, but `_bmad-output/implementation-artifacts/sprint-status.yaml` tracks 22 older/composite story keys generated on 2026-07-09.
   - Examples: current Stories 2.1a, 2.1b, and 2.1c are collapsed into `2-1-create-and-validate-project-bindings`; current Stories 3.6d and 3.6e are missing; current Stories 5.2b-5.2e and 5.3a-5.3c are represented by older/composite keys.
   - Impact: non-interactive story creation or implementation automation would use the wrong queue and could skip or merge stories that the current epics deliberately split.
   - Recommendation: regenerate or update `sprint-status.yaml` from the current `epics.md` before starting implementation automation.

### Major Issues

1. **Provider-dependent story completion still depends on unproven external Archon producer output.**
   - Evidence: the isolated handoff contract states that external Archon producer completion status is not proven and provider-dependent Hermes stories must keep Archon dependency records until compatible producer output is available and validated.
   - Impact: local fixtures are valid and useful for consumer-side development, but provider-dependent stories cannot be marked complete from fixtures alone.
   - Recommendation: before marking provider-dependent Hermes stories done, validate against compatible Archon producer output or record those stories as blocked on the matching Archon stories.

### Minor Concerns

1. **Story 2.3 includes one future-story validation statement in its acceptance criteria.**
   - Evidence: one Story 2.3 criterion says Story 3.4a must reuse the Story 2.3 cwd guard when the real provider adapter exists.
   - Impact: the Story 2.3 blocking behavior correctly says Archon adapter cwd evidence remains in Story 3.4a and must not block Story 2.3, so this does not break the story. It is still cleaner as an integration note or Story 3.4a acceptance criterion.
   - Recommendation: optionally move that criterion to Story 3.4a or leave it as a non-blocking integration note.

### Best Practices Checklist

| Check | Result |
| --- | --- |
| Epics deliver user value | Pass |
| Epics avoid pure technical milestones | Pass |
| Hermes-owned stories avoid forward dependencies | Pass |
| Stories are sized around one implementation responsibility | Pass |
| Acceptance criteria are present and testable | Pass |
| Traceability to FRs is maintained | Pass |
| Local contract fixtures validate | Pass |
| Implementation tracking matches current stories | Fail |

## Summary and Recommendations

### Overall Readiness Status

NOT READY.

The core planning artifacts are substantially aligned: PRD, architecture, epics, and UX are present; PRD FR coverage is 100%; UX and architecture agree on the headless v1 boundary; and the local Workflow Commander contract package validates successfully.

Implementation should not start through the current automation queue because the implementation tracking artifact is stale and does not match the current epics. Provider-dependent story completion also remains constrained by unproven external Archon producer output.

### Issue Counts

- Critical: 1
- Major: 1
- Minor: 1
- Warnings: 0

### Critical Issues Requiring Immediate Action

1. Regenerate or update `_bmad-output/implementation-artifacts/sprint-status.yaml` from the current `_bmad-output/planning-artifacts/epics.md`.
   - Current epics define 30 stories.
   - Current sprint status tracks 22 older/composite story keys.
   - Automation that uses the stale sprint status could skip split stories or create implementation work from obsolete names.

### Major Issues Requiring Resolution Before Completion Claims

1. Validate provider-dependent Hermes stories against compatible Archon producer output before marking those stories done.
   - Local schemas and fixtures validate.
   - External Archon producer completion remains unproven in this local handoff.
   - Provider-dependent stories must retain their Archon dependency records until compatible producer output is available and validated.

### Recommended Next Steps

1. Regenerate `sprint-status.yaml` so it contains the current 30 story keys from `epics.md`, including split stories 2.1a-2.1c, 3.6d-3.6e, 5.2b-5.2e, and 5.3a-5.3c.
2. Decide whether to move the future-story validation sentence from Story 2.3 into Story 3.4a or leave it as a non-blocking integration note.
3. Keep provider-dependent stories blocked from completion until compatible Archon producer output has been validated against the local contract package.

### Final Note

This assessment identified 3 issues across 3 severity categories. Address the critical tracking mismatch before proceeding to implementation automation. The planning documents themselves are close, but the handoff is not ready while the implementation queue points at stale story structure.

Assessor: Codex using `bmad-check-implementation-readiness` in non-interactive automation mode.
