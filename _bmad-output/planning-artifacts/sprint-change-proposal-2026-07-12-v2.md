---
project: hermes-agent
date: 2026-07-12
status: approved
mode: incremental
scopeClassification: moderate
approval: approved
approvedBy: kevin
approvedAt: 2026-07-12
sourceReport: implementation-readiness-report-2026-07-12.md
supersedes: sprint-change-proposal-2026-07-12.md
---

# Sprint Change Proposal: Close Workflow Commander Readiness Gaps

**Date:** 2026-07-12
**Project:** hermes-agent
**Requested by:** kevin
**Review mode:** Incremental
**Status:** Approved for implementation handoff

## 1. Issue Summary

The implementation-readiness assessment rates the Hermes Workflow Commander handoff `NOT READY`.
The PRD, architecture, epics, and headless UX contract remain aligned, and all 17 functional requirements have explicit story coverage.
The readiness failure is caused by incomplete contract evidence and incomplete story-level acceptance criteria.

Three critical evidence blockers remain:

1. No captured external Archon producer runtime output is present for provider binding, command, workflow-event, or delivery and outbox families.
2. The gate-decision schemas exist only as an unvalidated record contract, with no required behavior-case schema or example family.
3. The operational-diagnostic schema exists only as an unvalidated partial record contract, with no required behavior-case schema or example family.

The story review found six major acceptance gaps and one minor failure-path gap in Stories 2.1c, 2.5, 4.1, 4.3, 5.2a, 5.2c, and 5.3c.

### Evidence

- The readiness report records 3 critical blockers, 6 major issues, and 1 minor issue.
- Nine JSON schema files exist, while `validate_contracts.py` requires and reports only seven.
- No gate-decision or operational-diagnostic example family exists under `contracts/workflow-commander/examples/`.
- The contract README omits both contract areas from its canonical inventory and validation rules.
- `epics.md` explicitly states that no captured external Archon producer runtime output is present in the isolated handoff.
- Every affected story remains in backlog, so correction can occur before implementation begins.
- `sprint-status.yaml` contains an absolute `story_location` from another workspace.

### Problem Classification

This is an incomplete translation of existing requirements into testable story criteria, combined with incomplete evidence contracts.
It is not a new product requirement, strategic pivot, failed implementation approach, or MVP scope change.

## 2. Impact Analysis

### Epic Impact

No epic needs to be added, removed, renumbered, resequenced, or redefined.

| Epic | Impact |
| --- | --- |
| Epic 2 | Strengthen binding lifecycle and materialization acceptance criteria in Stories 2.1c and 2.5. |
| Epic 3 | Preserve the provider completion gate and add an executable external evidence validation handoff. |
| Epic 4 | Strengthen uninterrupted combined-workflow and replay-safe gate-decision criteria in Stories 4.1 and 4.3. |
| Epic 5 | Strengthen BMAD drift, gateway-downtime reconciliation, and failed diagnostic recovery criteria in Stories 5.2a, 5.2c, and 5.3c. |

All existing dependency direction remains valid.
Local fixture work may support Hermes-side implementation where individual stories permit it, but provider-dependent completion remains blocked until real Archon output passes compatibility validation.

### Story Impact

The seven affected stories remain correctly placed and ordered.
Only acceptance criteria, contract evidence, and validation gates need correction.
No forward Hermes dependency or circular dependency is introduced.

### Artifact Conflicts

| Artifact | Change Required |
| --- | --- |
| `prd.md` | None. Existing FRs and NFRs already require the missing behavior. |
| `architecture.md` | Correct schema and fixture inventories and add explicit local and external validation gates. |
| `epics.md` | Add approved acceptance criteria to seven stories and make the provider completion gate executable. |
| `ux-headless-interaction-contract.md` | None. Existing headless interactions already require explicit decisions, recovery, provenance, and redaction. |
| Gate-decision contracts | Harden replay and conditional-decision semantics and add behavior fixtures. |
| Operational-diagnostic contracts | Add complete family, lifecycle, provenance, redaction, and recovery-history semantics and fixtures. |
| `validate_contracts.py` | Require and validate every canonical schema and fixture family and support external Archon evidence validation. |
| Contract README | Add canonical files, rules, inventories, and completion commands. |
| Isolated handoff contract | Update inventory counts and add an executable external producer completion gate. |
| `sprint-status.yaml` | Regenerate the stale workspace-specific `story_location` without changing work status. |

### Technical Impact

This proposal corrects planning and shared contract evidence before production Workflow Commander implementation begins.
It does not authorize a new runtime service, database, queue, frontend, core model tool, user-facing environment variable, deployment change, infrastructure change, monitoring system, or CI/CD redesign.

## 3. Recommended Approach

Use **Direct Adjustment** within the existing epic structure.

The product scope and architecture remain valid.
Rollback provides no benefit because all affected stories remain in backlog.
MVP reduction would remove required safety, auditability, or reconciliation behavior without solving the evidence problem.

### Effort, Risk, And Timeline

- **Effort:** Medium.
- **Risk:** Medium until schema and fixture semantics are implemented and validator-backed; low afterward.
- **Timeline impact:** Correct planning and local contract evidence before committing affected stories to implementation.
- **External dependency:** Provider-dependent completion remains blocked until the Archon owner supplies real, redacted producer output and it passes compatibility validation.

### Sequencing

1. Apply the approved acceptance criteria to the seven affected stories.
2. Harden the gate-decision and operational-diagnostic contract schemas.
3. Add both behavior-case schemas and the required local fixture families.
4. Extend the validator and contract documentation.
5. Update architecture and isolated-handoff inventory statements.
6. Regenerate sprint metadata from the current workspace without changing backlog state.
7. Obtain and validate real Archon producer evidence.
8. Re-run implementation readiness.

## 4. Detailed Change Proposals

### A. Story Acceptance Criteria

#### Story 2.1c: Manage Project Binding Lifecycle And Status

**Section:** Acceptance Criteria

**Current:**

```text
- Given an existing Project Binding has valid updated metadata, when an authorized command updates it, then Hermes preserves binding id, audit history, and validation-state transition.
- Given a Project Binding is disabled, when BMAD or provider action is requested through that binding, then Hermes blocks the action and explains that the binding must be enabled and valid.
- Given at least one Project Binding exists, when status is queried, then Hermes returns all required binding and validation fields in a versioned structured result.
```

**Proposed:**

```text
- Given an existing Project Binding has valid updated metadata, when an authorized command updates it, then Hermes preserves binding id, audit history, and validation-state transition.
- Given a Project Binding is disabled, when BMAD or provider action is requested through that binding, then Hermes blocks the action and explains that the binding must be enabled and valid.
- Given at least one Project Binding exists, when status is queried, then Hermes returns all required binding and validation fields in a versioned structured result.
- Given a disabled or invalid Project Binding has corrected cwd, GitHub, BMAD mount, or provider metadata, when an authorized caller requests repair, then Hermes preserves binding identity and audit history, reruns every required validation check, and keeps the binding disabled until validation succeeds.
- Given a repaired Project Binding passes all required validation checks, when an authorized caller re-enables it, then Hermes records the re-enable transition and permits project-bound actions; if validation fails, then Hermes keeps the binding disabled and returns actionable diagnostics without partial activation.
```

**Rationale:** The story promises repair and re-enable behavior but currently tests only update, disable, and query.

#### Story 2.5: Materialize Sprint Status Into Project Work Items

**Section:** Acceptance Criteria

**Current:**

```text
- Given an enabled Project Binding with a valid Bound Project Cwd, when materialization runs, then Hermes reads `sprint-status.yaml` only from that cwd and rejects missing, malformed, or unsupported data before mutation.
- Given a BMAD story changes in `sprint-status.yaml`, when materialization runs again, then Hermes derives the same Project Work Item identity and updates the existing item without including phase kind in the identity.
- Given materialization partially fails after validation begins, when Hermes reports the failure, then provenance identifies affected binding, source file, epic, story, or Project Work Item.
```

**Proposed:**

```text
- Given an enabled Project Binding with a valid Bound Project Cwd and valid `sprint-status.yaml` containing a new epic and story, when materialization runs, then Hermes creates exactly one Project Work Item for each selected BMAD epic or story identity and stores the binding reference, source artifact path, observed BMAD status, and source provenance.
- Given an enabled Project Binding with a valid Bound Project Cwd, when materialization runs, then Hermes reads `sprint-status.yaml` only from that cwd and rejects missing, malformed, or unsupported data before mutation.
- Given the same unchanged BMAD epic or story is materialized again, when Hermes derives its identity, then Hermes reuses the existing Project Work Item, performs an idempotent no-op or provenance refresh, and creates no duplicate Project Work Item or Phase Task.
- Given a BMAD story changes in `sprint-status.yaml`, when materialization runs again, then Hermes derives the same Project Work Item identity and updates the existing item without including phase kind in the identity.
- Given Hermes runtime state has advanced after materialization, when `sprint-status.yaml` is read again, then Hermes records the observed BMAD planning state without treating it as the runtime queue or overwriting Hermes-owned Kanban, gate, workflow, or next-action state.
- Given materialization partially fails after validation begins, when Hermes reports the failure, then provenance identifies affected binding, source file, epic, story, or Project Work Item.
```

**Rationale:** FR-5 requires initial creation, repeat-run idempotency, provenance, and separation between BMAD planning state and Hermes runtime state.

#### Story 4.1: Run Story Workflow

**Section:** Acceptance Criteria

**Current:**

```text
- Given a Project Work Item has a Phase Task, when the user starts the story workflow from Hermes, then Hermes starts the configured combined story workflow and records the workflow run reference on the Phase Task.
- Given the combined workflow is running, when status is checked from Hermes, then Hermes returns structured workflow progress without requiring the provider dashboard.
```

**Proposed:**

```text
- Given a Project Work Item has a Phase Task, when the user starts the story workflow from Hermes, then Hermes starts the configured combined story workflow and records the workflow run reference on the Phase Task.
- Given the combined workflow is running, when status is checked from Hermes, then Hermes returns structured workflow progress without requiring the provider dashboard.
- Given the provider-controlled combined workflow advances from story creation through implementation, fix loop, and review, when intermediate phases complete, then Hermes records progress without creating a Hermes-side pause or human gate before provider completion evidence triggers Done Verification.
```

**Rationale:** FR-12 requires uninterrupted provider-controlled progression before Done Verification.

#### Story 4.3: Capture Human Gate Decisions And Evidence

**Section:** Acceptance Criteria insertion after provider-command association

**Current:**

```text
- Given a gate decision requires a provider approval, rejection, resume, or retry command, when Hermes records the human decision, then Hermes sends the matching command through the strict provider adapter and records the command result separately from the human decision record.
```

**Proposed:**

```text
- Given a gate decision requires a provider approval, rejection, resume, or retry command, when Hermes records the human decision, then Hermes sends the matching command through the strict provider adapter and records the command result separately from the human decision record.
- Given Hermes receives the same authorized gate decision id or idempotency key more than once, when decision processing is replayed, then Hermes returns the original persisted decision outcome, applies exactly one phase transition, and does not send a duplicate provider control command.
```

**Rationale:** NFR-4 requires replay-safe gate decisions and duplicate-command prevention.

#### Story 5.2a: Reconcile BMAD Materialization Drift

**Section:** Acceptance Criteria

**Current:**

```text
- Given BMAD story artifact state changes after materialization, when reconciliation runs, then Hermes detects whether the Project Work Item needs update without duplicating Project Work Items or Phase Tasks.
- Given reconciliation performs deterministic repair, when Story Status History or diagnostics are queried, then Hermes returns what was repaired, why it was deterministic, and which BMAD source records supported it.
```

**Proposed:**

```text
- Given BMAD story artifact state changes after materialization, when reconciliation runs, then Hermes detects whether the Project Work Item needs update without duplicating Project Work Items or Phase Tasks.
- Given BMAD source state is missing or malformed, when reconciliation runs, then Hermes preserves the last known Hermes runtime state, records a source-linked diagnostic, and applies no Project Work Item, Phase Task, gate, or workflow mutation.
- Given BMAD source state is unchanged, when reconciliation runs repeatedly, then Hermes records an idempotent no-op or observation result and creates no duplicate Project Work Item, Phase Task, gate, workflow reference, or history transition.
- Given deterministic repair is applied more than once for the same source version, when reconciliation repeats, then Hermes reuses the original identities and repair result without duplicate mutation.
- Given reconciliation performs deterministic repair, when Story Status History or diagnostics are queried, then Hermes returns what was repaired, why it was deterministic, and which BMAD source records supported it.
```

**Rationale:** The story's completion gate names missing, malformed, changed, unchanged, and duplicate-safe cases, while its criteria cover only changed state and repair reporting.

#### Story 5.2c: Reconcile Workflow Event Delivery Evidence

**Section:** Acceptance Criteria

**Current:**

```text
- Given event delivery is duplicated, delayed, terminally failed, or absent after provider completion, when reconciliation evaluates evidence, then Hermes links evidence to affected workflow run and records delivery-drift category without duplicate mutation.
```

**Proposed:**

```text
- Given event delivery is duplicated, delayed, terminally failed, or absent after provider completion, when reconciliation evaluates evidence, then Hermes links evidence to the affected workflow run and records the delivery-drift category without duplicate mutation.
- Given the gateway is unavailable while provider workflow state advances, when the gateway returns and reconciliation compares provider state, delivery health, and persisted event receipts, then Hermes classifies missed delivery, projects only deterministic state, preserves idempotency, and creates no duplicate workflow reference, Phase Task transition, gate, comment, or Story Status History entry.
```

**Rationale:** NFR-2 explicitly requires gateway-downtime reconciliation.

#### Story 5.3c: Resolve Diagnostics And Preserve Audit History

**Section:** Acceptance Criteria

**Current:**

```text
- Given a diagnostic has been resolved, when reconciliation or authorized action clears the issue, then Hermes records resolution source, timestamp, recovery action, and resulting state while keeping prior diagnostic history available for audit.
```

**Proposed:**

```text
- Given a diagnostic has been resolved, when reconciliation or authorized action clears the issue, then Hermes records resolution source, timestamp, recovery action, and resulting state while keeping prior diagnostic history available for audit.
- Given a recovery command fails, returns incompatible output, or cannot prove resolution, when Hermes records the recovery attempt, then Hermes keeps the diagnostic active, appends the failed attempt with redacted command evidence and timestamp, and preserves all prior diagnostic history without reporting the issue as resolved.
```

**Rationale:** Failed recovery must remain auditable and must not clear an active diagnostic.

### B. Gate-Decision Contract Family

Affected artifacts are `gate-decision-record.schema.json`, a new `gate-decision-case.schema.json`, and a new `examples/gate-decisions/` family.

The corrected contract will:

1. Define `decisionId` as the canonical replay and idempotency key.
2. Require rejection decisions to include a non-empty reason and a non-`none` recovery action.
3. Constrain approval to the allowed completed phase state.
4. Record provider command action, correlation reference, and outcome separately from the human decision.
5. Express input decisions, persisted outcomes, expected phase transitions, and expected provider-command counts through behavior cases.
6. Add eight cases: approval, four rejection recovery routes, delayed pending decision, replayed approval, and provider-command failure association.
7. Prove one durable decision, one phase transition, and at most one provider command per replay key.

### C. Operational-Diagnostic Contract Family

Affected artifacts are `operational-diagnostic.schema.json`, a new `operational-diagnostic-case.schema.json`, and a new `examples/operational-diagnostics/` family.

The corrected contract will:

1. Require diagnostic family, lifecycle state, source provenance, affected references, evidence references, redaction state, owner, and recovery options.
2. Add `external_delay` to next-action ownership.
3. Add append-only resolution and recovery-attempt history.
4. Require failed recovery to preserve active diagnostic state.
5. Make redaction-before-persistence an explicit invariant.
6. Add ten cases covering all eight diagnostic families, successful resolution, and failed recovery.
7. Validate family, owner, recovery, provenance, redaction, lifecycle, and immutable history relationships.

### D. Contract Validator

Update `validate_contracts.py` to:

1. Require all 11 canonical schemas.
2. Require and count all gate-decision and operational-diagnostic cases.
3. Reject missing and unexpected examples in both families.
4. Validate decision replay, transition uniqueness, command uniqueness, conditional decisions, diagnostic compatibility, redaction, active-state preservation, and append-only recovery history.
5. Add `--archon-evidence <path>` for redacted captured producer output.
6. Add `--require-archon-evidence` as the provider-dependent completion gate.
7. Keep local validation deterministic, offline, and isolated from parent workspaces.
8. Reject secrets, raw signatures, unsafe command output, symlinks, and host-specific paths in captured evidence.

### E. Contract README

Update the contract README to list all schemas and fixtures, document gate and diagnostic rules, report exact counts, and distinguish local fixture readiness from external producer compatibility.
Document both validation commands:

```text
uv run python _bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py
uv run python _bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py --archon-evidence <path> --require-archon-evidence
```

### F. Epics Provider Completion Gate

Add the executable external evidence completion command to the existing Provider Completion Gate.
Keep every Archon dependency record on provider-dependent stories.
State that fixture-only validation is insufficient for provider-dependent completion and that captured evidence must exclude secrets, raw signatures, and unsafe command output.

### G. Architecture Contract Reality

Update `architecture.md` to report 11 canonical schemas and 83 examples: 65 existing examples, 8 gate-decision cases, and 10 operational-diagnostic cases.
Strengthen the gate and diagnostic validation rows and add the external completion command.
Leave AD-1 through AD-10, the structural seed, runtime stack, ownership boundaries, and headless scope unchanged.

### H. Cross-Project Isolated Handoff Contract

Update the isolated handoff inventory to 11 schemas and 83 examples.
Add the two new fixture families and both validation commands.
Require the external evidence gate before provider-dependent completion while preserving isolation, ownership, and redaction rules.

### I. Sprint Tracker

Regenerate `_bmad-output/implementation-artifacts/sprint-status.yaml` from the current checkout.
Correct `story_location` and timestamps while preserving every epic and story as `backlog`, every retrospective as `optional`, all identifiers, and the provider-dependent completion note.

## 5. Implementation Handoff

### Scope Classification

**Moderate** — Product Owner and Developer coordination is required for backlog text, shared contracts, validator behavior, documentation, and sprint metadata.
No Product Manager or Solution Architect replan is required unless contract hardening reveals a fundamental cross-project incompatibility.

### Product Owner Responsibilities

- Apply the seven approved acceptance-criteria changes to `epics.md`.
- Preserve existing FR and NFR traceability, story IDs, dependency direction, and headless scope.
- Keep affected stories in backlog until their corrected criteria and local evidence gates exist.

### Hermes Developer Responsibilities

- Harden the local gate-decision and operational-diagnostic schemas.
- Add both behavior-case schemas and all required fixtures.
- Extend validator invariants and external evidence validation.
- Update the contract README, architecture reality statements, isolated handoff inventory, and sprint metadata.
- Run local validation from the supported project runtime.
- Do not mark provider-dependent stories done from local fixtures alone.

### Archon Producer Responsibilities

- Capture redacted runtime output for provider binding lifecycle, workflow commands, workflow events, and delivery or outbox status.
- Exclude secrets, raw signatures, and unsafe command content.
- Validate every captured family against the shared contract package.
- Resolve producer and consumer incompatibilities before provider-dependent Hermes story completion.

### Success Criteria

- `epics.md` contains all seven approved acceptance-criteria corrections.
- Every canonical schema is required and validated.
- Gate-decision and operational-diagnostic fixture families exist, are counted, and pass validation.
- Gate replay, delayed decisions, diagnostic redaction, all diagnostic families, successful resolution, and failed recovery are validated.
- The contract README, architecture, and isolated handoff report the actual package inventory accurately.
- Sprint metadata points to the current workspace and retains unchanged backlog state.
- Real Archon producer evidence is captured and passes the explicit external evidence validation mode.
- A fresh implementation-readiness assessment reports no critical evidence blockers or story acceptance gaps.

## 6. Checklist Summary

| Checklist Area | Status | Finding |
| --- | --- | --- |
| Trigger and context | Done | The readiness report and filesystem evidence establish the change. |
| Epic impact | Done | Existing epics remain valid; seven stories need criteria changes. |
| Artifact conflict analysis | Done | PRD and UX remain unchanged; epics, contracts, validator, documentation, and sprint metadata need correction. |
| Path forward | Done | Direct Adjustment is preferred over rollback or MVP reduction. |
| Specific edit review | Done | All 15 incremental edit proposals were approved. |
| User approval | Done | Kevin explicitly approved the complete proposal on 2026-07-12. |
| Sprint status restructuring | Not applicable | No epic or story IDs change. Metadata regeneration remains an implementation handoff item. |
| Handoff | Done | Routed to Product Owner, Hermes Developer, and Archon producer owner. |

## 7. Approval Decision

Kevin explicitly approved this Sprint Change Proposal on 2026-07-12 after incremental review of all 15 edit proposals.
Approval authorizes the documented planning, contract, validator, documentation, and sprint-metadata corrections.
Approval does not authorize fabricated external evidence, provider-dependent completion claims without validated producer output, or production scope beyond this proposal.

This v2 proposal supersedes `sprint-change-proposal-2026-07-12.md` while preserving that file as historical context.

## 8. Workflow Execution And Handoff Log

| Field | Recorded Outcome |
| --- | --- |
| Issue addressed | Workflow Commander readiness failure caused by three evidence blockers and seven story acceptance gaps. |
| Change scope | Moderate. |
| Artifacts proposed for modification | `epics.md`, `architecture.md`, contract schemas, behavior-case schemas, contract examples, `validate_contracts.py`, contract README, isolated handoff contract, and `sprint-status.yaml`. |
| Artifacts intentionally unchanged | `prd.md`, `ux-headless-interaction-contract.md`, runtime infrastructure, and production code outside the approved correction scope. |
| Routed to | Product Owner, Hermes Developer, and Archon producer owner. |
| Product Owner handoff | Apply the seven approved story acceptance-criteria corrections while preserving IDs, ordering, traceability, and backlog state. |
| Hermes Developer handoff | Harden contracts, add fixtures, extend validation, update inventories, and regenerate sprint metadata. |
| Archon producer handoff | Supply redacted runtime evidence and validate producer compatibility. |
| Completion gate | Re-run implementation readiness only after local contract evidence and external producer evidence are present and validated. |
| Approval | Explicitly approved by kevin on 2026-07-12. |

### Checklist Completion

- `[x]` Trigger and context established with concrete evidence.
- `[x]` Epic and story impact assessed.
- `[x]` PRD, architecture, UX, contract, documentation, and sprint impacts assessed.
- `[x]` Direct Adjustment selected over rollback or MVP reduction.
- `[x]` All 15 detailed edit proposals reviewed incrementally and approved.
- `[x]` Explicit user approval obtained.
- `[N/A]` Sprint status restructuring is unnecessary because no epic or story IDs change.
- `[x]` Handoff roles, sequence, and success criteria confirmed.
