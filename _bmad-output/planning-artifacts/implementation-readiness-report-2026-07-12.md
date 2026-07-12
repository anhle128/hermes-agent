---
project: hermes-agent
date: 2026-07-12
status: final
readinessStatus: NOT_READY
issueCounts:
  critical: 3
  major: 0
  minor: 1
  warnings: 1
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
selectedArtifacts:
  prd: _bmad-output/planning-artifacts/prd.md
  architecture: _bmad-output/planning-artifacts/architecture.md
  epics: _bmad-output/planning-artifacts/epics.md
  ux: _bmad-output/planning-artifacts/ux-headless-interaction-contract.md
automationMode: true
---

# Implementation Readiness Assessment Report

**Date:** 2026-07-12
**Project:** hermes-agent

## Step 1: Document Discovery

### PRD Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/prd.md` (16253 bytes, modified 2026-07-12 06:13:53 +07)

**Sharded Documents:**
- None found.

### Architecture Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/architecture.md` (11708 bytes, modified 2026-07-12 06:14:16 +07)

**Sharded Documents:**
- None found.

### Epics & Stories Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/epics.md` (68177 bytes, modified 2026-07-12 06:53:28 +07)

**Sharded Documents:**
- None found.

### UX Design Files Found

**Whole Documents:**
- `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md` (3533 bytes, modified 2026-07-12 06:15:33 +07)

**Sharded Documents:**
- None found.

### Discovery Issues

- No whole/sharded duplicate document formats were found for PRD, architecture, epics, or UX.
- No required planning document was missing from the configured planning artifact folder.

### Selected Documents

- PRD: `_bmad-output/planning-artifacts/prd.md`
- Architecture: `_bmad-output/planning-artifacts/architecture.md`
- Epics & stories: `_bmad-output/planning-artifacts/epics.md`
- UX: `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md`

## Step 2: PRD Analysis

### Functional Requirements

FR-1: Create and view Project Bindings. Hermes can create, view, update, disable, and validate a Project Binding with profile identity, Bound Project Cwd, GitHub reference, BMAD skill directory reference, workflow provider binding metadata, and display name. Hermes rejects invalid cwd values and returns the active binding before starting any BMAD or provider action. Hermes persists enough binding metadata to reconstruct status after restart. Hermes reports provider binding status as missing, valid, stale, disabled, rotated, or conflicting when that evidence is available.

FR-2: Mount project-local BMAD skills. Hermes can add the bound project's BMAD skill directory to the selected profile's `skills.external_dirs` and reload that profile's skill index. Hermes records the source directory for mounted BMAD skills. Hermes does not use global skills as the primary BMAD mount for multi-project control. Hermes detects missing and wrong-project BMAD mounts.

FR-3: Enforce Bound Project Cwd for workflow actions. Hermes runs BMAD and provider actions for a Project Binding from the Bound Project Cwd unless a requirement explicitly states otherwise. BMAD artifacts created through Hermes land under the bound project's configured output location. Hermes blocks actions when the selected Project Binding lacks a valid cwd. Hermes audit records include the cwd used for each workflow action. Hermes does not infer cwd from skill visibility alone.

FR-4: Invoke BMAD planning workflows from Hermes. Hermes can invoke selected BMAD planning workflows for brainstorming, product brief, PRD, architecture, epics, stories, sprint status, create-story, and dev-story preparation from the Bound Project Cwd. Hermes presents BMAD as a behind-the-scenes workflow engine, records produced artifact paths, and preserves Project Binding context on failure. Hermes can continue orchestration from generated BMAD artifacts in the bound project.

FR-5: Materialize sprint status into Project Work Items. Hermes can read `sprint-status.yaml` from the Bound Project Cwd and idempotently create or update Project Work Items for BMAD epics and stories. Re-running materialization updates existing Project Work Items instead of duplicating them. Hermes stores BMAD artifact references and observed planning status on each Project Work Item. Hermes does not treat `sprint-status.yaml` as the runtime queue after materialization.

FR-6: Maintain Hermes-owned operational backlog. Hermes persists operational backlog, selected story, phase metadata, workflow references, human gate metadata, and next action as operational project-work state. Hermes exposes that state through structured command, agent, or API results. Hermes keeps canonical Kanban lifecycle values unchanged: `triage`, `todo`, `ready`, `running`, `blocked`, `done`, and `archived`.

FR-7: Consume generic workflow provider bindings. Hermes can register or inspect provider-side workflow bindings through generic `provider` and `name` vocabulary. Hermes detects disagreement between the Project Binding and provider binding metadata. Hermes surfaces missing, stale, disabled, rotated, and conflicting provider binding states as actionable diagnostics. Archon owns producer-side provider binding persistence and status production.

FR-8: Control provider workflows through provider adapters. Hermes can start, inspect, approve, reject, resume, retry, and cancel provider workflow runs through the adapter selected by the Project Binding. For provider `archon`, Hermes consumes parseable CLI JSON through the provider adapter. Hermes captures stdout, stderr, exit code, cwd when applicable, timeout, correlation id, and parsed result. Hermes fails closed on malformed JSON, incompatible schema version, timeout, unexpected exit code, or unexpected state. Hermes does not use provider HTTP APIs for the `archon` state-changing control path.

FR-9: Receive typed workflow provider events. Hermes receives signed workflow provider events on `/p/{profile}/webhooks/workflow-events/{provider}` and mutates project work only after schema, binding, replay, idempotency, provider, profile, and authorization validation pass. Hermes rejects unknown Project Binding, wrong profile, wrong codebase, stale timestamp, duplicate event id, invalid signature, unsupported provider, and schema failure before mutation. Hermes stores accepted event ids and idempotency keys so duplicate delivery is safe. Hermes maps completion, failure, approval-request, and artifact events only to the intended Project Work Item or Phase Task.

FR-10: Return provider event delivery and outbox health. Hermes can return structured provider event-delivery status identifying healthy, delayed, failed, duplicated, terminal failure, or reconciliation-pending state. Hermes exposes this evidence through Story Status History and diagnostics. Hermes does not block provider workflow execution solely because event notification failed. Archon owns producer-side outbox and delivery-health status for provider `archon`.

FR-11: Create one Phase Task per BMAD story. Hermes materializes each selected BMAD story as a single Phase Task. The Phase Task links to one Project Work Item and shares Story Status History evidence. Repeated materialization must not duplicate Phase Tasks.

FR-12: Run the combined story workflow. Hermes can run the configured combined story workflow for a selected BMAD story. Hermes records the provider workflow run reference on the Phase Task. The workflow can run story creation through review without a Hermes-side pause between phases.

FR-13: Gate Done Verification. Hermes blocks the Phase Task for a Done Verification Gate after provider completion evidence arrives. Human approval completes the Phase Task. Human rejection routes to rerun, resume, retry, or recovery without marking the story complete.

FR-14: Collect human decisions from Hermes. Hermes can publish or return structured gate evidence, accept approval or rejection through an authorized command or agent interaction, persist the decision, and send the matching provider command when required. Each gate decision records actor, timestamp, gate kind, decision, reason when present, and evidence references. Hermes does not auto-continue past a HILT Gate unless an explicit persisted policy later permits it.

FR-15: Return unified Story Status History. Hermes can return one source-labeled Story Status History containing BMAD milestones, Project Work Item state, Phase Task state, provider run references, workflow events, GitHub PR references, HILT Gate decisions, provenance, and next action. The history distinguishes BMAD planning lifecycle from Hermes runtime lifecycle. The history distinguishes GitHub PR merge state from Done Verification state.

FR-16: Reconcile cross-system state. Hermes compares BMAD artifact state, provider workflow state, GitHub PR state, Hermes Project Work Item state, and HILT Gate state to detect drift. Hermes may repair deterministic projection drift. Hermes must not auto-approve HILT Gates or mark stories complete when evidence conflicts.

FR-17: Provide operational diagnostics. Hermes surfaces binding conflicts, cwd problems, missing BMAD artifacts, unsupported sprint status, provider command contract gaps, event delivery failures, duplicate workflow events, outbox backlog, stale PR references, and unresolved gates. Diagnostics distinguish user action, configuration action, Hermes automation, provider action, BMAD action, GitHub action, implementation-agent action, and external delay. Diagnostics include recovery guidance and redact secrets.

**Total FRs:** 17

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

**Total NFRs:** 17

### Additional Requirements

- Workflow Commander v1 is headless: commands, agent interactions, structured API or command results, durable records, and optional existing notification transports only.
- Hermes must not ship a dedicated Workflow Commander dashboard, graphical Kanban board, gate screen, timeline screen, desktop view, web application, or marketing surface in v1.
- Hermes must preserve the ownership boundary between Hermes, BMAD, Archon, and GitHub.
- The local contract package under `contracts/workflow-commander/schemas/` is a contract-gated dependency for downstream stories.
- Required example fixture families must exist under `contracts/workflow-commander/examples/` and pass compatibility tests before matching downstream stories can claim fixture readiness.
- Downstream implementation workflows must run from the `hermes-agent` subproject root.
- Candidate validation commands are `uv sync --extra dev`, `uv run pytest`, and `uv run ruff check .`.

### PRD Completeness Assessment

The PRD provides a complete numbered FR/NFR baseline with clear ownership boundaries, product non-goals, and validation constraints. Remaining readiness depends on whether the epics, architecture, UX/headless interaction contract, story dependencies, and local contract evidence fully trace back to this baseline.

## Step 3: Epic Coverage Validation

### Coverage Matrix

| FR Number | PRD Requirement | Epic / Story Coverage | Status |
| --- | --- | --- | --- |
| FR-1 | Create and view Project Bindings | Stories 2.1a, 2.1b, 2.1c | Covered |
| FR-2 | Mount project-local BMAD skills | Story 2.2 | Covered |
| FR-3 | Enforce Bound Project Cwd for workflow actions | Story 2.3 | Covered |
| FR-4 | Invoke BMAD planning workflows from Hermes | Story 2.4 | Covered |
| FR-5 | Materialize sprint status into Project Work Items | Story 2.5 | Covered |
| FR-6 | Maintain Hermes-owned operational backlog | Story 2.6 | Covered |
| FR-7 | Consume generic workflow provider bindings | Story 3.2 | Covered |
| FR-8 | Control provider workflows through provider adapters | Stories 3.4a, 3.4b, 3.4c | Covered |
| FR-9 | Receive typed workflow provider events | Stories 3.6a, 3.6b, 3.6c, 3.6d, 3.6e | Covered |
| FR-10 | Return provider event delivery and outbox health | Story 3.8 | Covered |
| FR-11 | Create one Phase Task per BMAD story | Stories 2.6, 3.6c | Covered |
| FR-12 | Run the combined story workflow | Stories 3.6c, 3.6e, 4.1 | Covered |
| FR-13 | Gate Done Verification | Stories 3.6d, 4.2 | Covered |
| FR-14 | Collect human decisions from Hermes | Stories 3.4b, 4.1, 4.2, 4.3 | Covered |
| FR-15 | Return unified Story Status History | Story 5.1 | Covered |
| FR-16 | Reconcile cross-system state | Stories 5.2a, 5.2b, 5.2c, 5.2d, 5.2e | Covered |
| FR-17 | Provide operational diagnostics | Stories 5.3a, 5.3b, 5.3c | Covered |

### Missing Requirements

- No PRD FRs are missing from the epics and stories document.
- No story-level FR claims were found for FR identifiers absent from the PRD.

### Coverage Statistics

- Total PRD FRs: 17
- FRs covered in epics: 17
- Coverage percentage: 100%

### Coverage Finding

The epics document provides complete FR traceability at the story level. Readiness still depends on later checks for architecture support, UX/headless interaction alignment, story quality, dependency evidence, and external provider validation constraints.

## Step 4: UX Alignment Assessment

### UX Document Status

Found: `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md`.

The UX artifact is intentionally a headless interaction contract. It defines the operator experience through Hermes commands, agent interactions, structured command/API results, durable records, Story Status History, diagnostics, and optional existing notification transports.

### UX To PRD Alignment

- Aligned: the UX contract repeats the PRD boundary that Workflow Commander v1 must not create a dedicated dashboard, graphical Kanban board, gate screen, timeline screen, desktop view, web application, or marketing surface.
- Aligned: the primary interaction patterns map to PRD user journeys and FRs: Project Binding inspection, BMAD workflow invocation, provider workflow control, Done Verification Gate, Story Status History, and operational diagnostics.
- Aligned: headless usability requirements map to PRD NFRs for recovery guidance, explicit human decisions, machine-readable structured results, redaction, durable state, and notification mirrors.
- No UX requirements were found that contradict or extend beyond the PRD scope.

### UX To Architecture Alignment

- Aligned: architecture AD-8 states Workflow Commander v1 does not add a new runtime service, cloud queue, shared database, or dedicated graphical frontend.
- Aligned: AD-3, AD-4, AD-5, and the consistency conventions support the required response shapes through provider adapters, signed events, Kanban-backed runtime project work, HILT gates, Story Status History, diagnostics, and reconciliation.
- Aligned: architecture validation gates require schema-versioned machine contracts and story-specific fixture validation for command results, workflow events, delivery status, gate decisions, and diagnostics.
- No unsupported UI components were found. Existing TUI, dashboard, web, and desktop stack references are brownfield stack context, not new Workflow Commander UX scope.

### Alignment Issues

- None found.

### Warnings

- The UX artifact is not a visual design spec. This is acceptable because the PRD and architecture define Workflow Commander v1 as headless.

## Step 5: Epic Quality Review

### Epic Structure Validation

| Epic | User Value Focus | Independence / Dependency Direction | Result |
| --- | --- | --- | --- |
| Epic 2: Project-Bound Planning And Work Backlog | Enables the operator to bind a project, mount BMAD, run planning, and materialize BMAD stories into Hermes project work. | Uses parent contract dependencies and earlier local stories only. No dependency on later local Hermes epics found. | Pass |
| Epic 3: Workflow Provider Control And Event Delivery | Enables provider binding, workflow control, event ingress, and delivery health without opening the provider dashboard. | Depends on Epic 2 substrate and external Archon/parent contract work. No dependency on later local Hermes epics found. | Pass with external evidence blocker |
| Epic 4: Human-Gated Story Execution | Enables running the combined story workflow and making human Done Verification decisions from Hermes. | Depends on Epic 2/3 substrate and external Archon contracts. No dependency on later local Hermes epics found. | Pass with external evidence blocker |
| Epic 5: Story Status History, Reconciliation, And Diagnostics | Enables users to understand status, reconcile drift, and recover from operational issues. | Depends on earlier local Hermes work and external contract/provider evidence. No dependency on later local Hermes epics found. | Pass with evidence blockers |

### Story Quality Assessment

- Story count checked: 30 local Hermes-owned implementation stories.
- All stories are framed as user stories with an actor, user need, and outcome.
- All stories include `Requirements Covered`, `Implementation Scope`, `Depends on`, `Contract needed`, `Blocking behavior`, `Integration validation`, and `Acceptance Criteria`.
- Acceptance criteria are predominantly Given/When/Then and testable.
- No story was found that depends on a later local Hermes story.
- No technical-only epic such as "setup database" or "create models" was found.
- Brownfield constraints are handled through architecture AD-8 and story-scoped changes rather than a broad starter-template setup story.

### Dependency Analysis

- Parent Story 1.3a/1.3b/1.3c dependencies are explicit contract-source dependencies, not hidden local future work.
- Archon dependencies are explicit producer-side dependencies, not Hermes-owned implementation work.
- Local Hermes sequencing is ordered: Epic 2 establishes Project Binding/materialization state; Epic 3 consumes it for provider control and events; Epic 4 consumes provider/gate foundations; Epic 5 consumes prior evidence for history, reconciliation, and diagnostics.
- The local handoff intentionally preserves parent story numbering and starts at Epic 2. This is documented in the epics frontmatter and overview.

### Critical Readiness Issues

#### CRIT-1: External Archon Producer Runtime Output Is Missing

The local handoff explicitly states that no captured external Archon producer runtime output is present. Provider-dependent Hermes stories cannot be marked done from local fixtures alone.

Affected areas include provider binding lifecycle, workflow command output, workflow event output, delivery/outbox status output, provider-driven story execution, gate command flow, provider/event reconciliation, and provider-sourced diagnostics.

Recommendation: capture external Archon producer output for the provider binding lifecycle, workflow commands, workflow events, and delivery/outbox status families, then validate it against the local `contracts/workflow-commander/` package before treating provider-dependent stories as completion-ready.

#### CRIT-2: Gate Decision Example Fixtures Are Not Present

The contract package includes `schemas/gate-decision-record.schema.json`, but no gate-decision example fixture family was found under `contracts/workflow-commander/examples/`.

Affected stories include Story 4.3 directly and downstream status/history or reconciliation stories that consume gate decision evidence.

Recommendation: add approval, rejection, recovery-routing, delayed-decision, and provider-command-associated gate decision examples and validate them before marking gate-consuming stories implementation-ready.

#### CRIT-3: Operational Diagnostic Example Fixtures Are Not Present

The contract package includes `schemas/operational-diagnostic.schema.json`, but no operational-diagnostic example fixture family was found under `contracts/workflow-commander/examples/`.

Affected stories include Stories 5.3a, 5.3b, and 5.3c. Story 5.3a requires examples for configuration, decision, external-delay, implementation-defect, duplicate-event, outbox, stale-PR, and unresolved-gate diagnostic families.

Recommendation: add operational diagnostic examples for every diagnostic family in the matrix, including redaction, next-action owner, recovery option, source provenance, resolution, and immutable-history cases.

### Major Issues

- None found in story structure, acceptance criteria shape, FR traceability, or local dependency direction.

### Minor Concerns

- MIN-1: The local Hermes story catalog starts at Epic 2 because parent story numbering is preserved. This is documented and not a blocker, but implementation tooling or readers that assume an Epic 1 local artifact may need explicit guidance.

### Quality Assessment Summary

The epic and story design is structurally strong and appropriately dependency-aware. The blocker is not poor story decomposition; it is insufficient completion evidence for provider-dependent, gate-decision, and diagnostic fixture families.

## Step 6: Summary and Recommendations

### Overall Readiness Status

**NOT READY**

The artifacts are strong enough to guide implementation planning, but they are not fully implementation-ready because required completion evidence is missing for provider-dependent stories, gate-decision fixtures, and operational diagnostic fixtures.

### Issue Counts

- Critical issues: 3
- Major issues: 0
- Minor concerns: 1
- Warnings: 1

### Critical Issues Requiring Immediate Action

1. **CRIT-1: External Archon producer runtime output is missing.** The isolated handoff states no captured external Archon producer output is present. Provider-dependent stories cannot be marked done until provider binding lifecycle output, workflow command output, workflow event output, and delivery/outbox status output are captured and validated against the local contract package.
2. **CRIT-2: Gate decision example fixtures are missing.** The gate-decision schema exists, but no approval/rejection/recovery gate-decision examples were found under `contracts/workflow-commander/examples/`.
3. **CRIT-3: Operational diagnostic example fixtures are missing.** The operational-diagnostic schema exists, but no diagnostic example family was found for the diagnostic matrix required by Stories 5.3a, 5.3b, and 5.3c.

### Positive Readiness Findings

- Required whole planning artifacts are present: PRD, architecture, epics/stories, and headless UX interaction contract.
- No whole/sharded duplicate artifact formats were found.
- PRD requirements are complete and numbered: 17 FRs and 17 NFRs.
- Epic/story FR coverage is complete: 17 of 17 PRD FRs are covered.
- The UX artifact aligns with the PRD and architecture by preserving the headless v1 product boundary.
- Story structure is strong: 30 local Hermes-owned stories, no local forward dependencies found, and acceptance criteria are generally testable.
- Local contract validation passed with `uv run python _bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py`.

Validation output summary:

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

### Recommended Next Steps

1. Capture external Archon producer runtime output for provider binding lifecycle, workflow command, workflow event, and delivery/outbox status families.
2. Validate the captured Archon output against `_bmad-output/planning-artifacts/contracts/workflow-commander/`.
3. Add gate-decision example fixtures for approval, rejection, delayed decision, recovery routing, and provider-command-associated decisions.
4. Add operational diagnostic examples for configuration, decision, external-delay, implementation-defect, duplicate-event, outbox, stale-PR, and unresolved-gate families.
5. Extend validation so gate-decision and operational-diagnostic example families are validated, not just schemas.
6. Re-run this readiness workflow after those artifacts are present.

### Final Note

This assessment identified 4 issues across evidence readiness and documentation caveats: 3 critical blockers and 1 minor concern. Address the critical blockers before treating the Hermes Workflow Commander handoff as implementation-ready.

**Assessor:** Codex running `bmad-check-implementation-readiness` in non-interactive automation mode.
