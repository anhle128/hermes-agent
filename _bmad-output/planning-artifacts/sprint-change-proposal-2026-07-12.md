---
project: hermes-agent
date: 2026-07-12
status: approved
mode: batch
scopeClassification: moderate
approval: approved
approvedBy: kevin
approvedAt: 2026-07-12
supersedes: sprint-change-proposal-2026-07-12.md prior content
sourceReport: implementation-readiness-report-2026-07-12.md
---

# Sprint Change Proposal: Close Workflow Commander Readiness Gaps

**Date:** 2026-07-12
**Project:** hermes-agent
**Requested by:** kevin
**Review mode:** Batch
**Status:** Approved for implementation handoff

## 1. Issue Summary

The current implementation-readiness assessment rates the Hermes Workflow Commander handoff `NOT READY`.
The PRD, architecture, epics, and headless UX contract remain aligned, and all 17 functional requirements have story coverage.
The readiness failure is caused by incomplete contract evidence and incomplete story-level acceptance criteria.

Three critical evidence blockers remain from the prior assessment:

1. No captured external Archon producer runtime output is present for provider binding, command, event, or delivery/outbox families.
2. The gate-decision schema exists, but no gate-decision example family is present or validated.
3. The operational-diagnostic schema exists, but no operational-diagnostic example family is present or validated.

The stricter story review also found six major acceptance gaps and one minor failure-path gap in Stories 2.1c, 2.5, 4.1, 4.3, 5.2a, 5.2c, and 5.3c.

### Evidence

- `schemas/` contains nine JSON schema files, including `gate-decision-record.schema.json` and `operational-diagnostic.schema.json`.
- `validate_contracts.py` lists only seven files in `REQUIRED_SCHEMA_FILES` and prints `Validated 7 schemas`.
- No gate-decision or operational-diagnostic examples exist under `contracts/workflow-commander/examples/`.
- The contract README omits both schemas from its canonical inventory and contains no rules for either fixture family.
- `epics.md` explicitly states that no captured external Archon producer output is present in the isolated handoff.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` shows every affected story as backlog, so correction can occur before implementation begins.
- The sprint tracker contains a stale absolute `story_location` from another workspace and must be regenerated before story creation.

## 2. Impact Analysis

### Epic Impact

No epic needs to be added, removed, renumbered, resequenced, or redefined.

| Epic | Impact |
| --- | --- |
| Epic 2 | Strengthen binding lifecycle and materialization acceptance criteria in Stories 2.1c and 2.5. |
| Epic 3 | Preserve the provider completion gate and add a concrete external evidence validation handoff. |
| Epic 4 | Strengthen uninterrupted combined-workflow and replay-safe gate-decision criteria in Stories 4.1 and 4.3. |
| Epic 5 | Strengthen BMAD drift, gateway-downtime reconciliation, and failed diagnostic recovery criteria in Stories 5.2a, 5.2c, and 5.3c. |

### Story Impact

The seven affected stories remain correctly placed and ordered.
Only acceptance criteria, contract dependencies, and validation evidence need correction.
No forward Hermes dependency or circular dependency is introduced.

### Artifact Conflicts

| Artifact | Change Required |
| --- | --- |
| `prd.md` | None. Existing FRs and NFRs already require the missing behavior. |
| `architecture.md` | Clarify actual schema/fixture coverage and external evidence validation gates. |
| `epics.md` | Add explicit acceptance criteria to seven stories and tighten contract evidence language. |
| `ux-headless-interaction-contract.md` | None. Existing headless interactions already require explicit decisions, recovery, provenance, and redaction. |
| Contract schemas | Harden gate-decision replay semantics and operational-diagnostic fields to match the stories. |
| Contract examples | Add gate-decision behavior and operational-diagnostic fixture families. |
| `validate_contracts.py` | Require and validate both schema/fixture families and support explicit external Archon evidence validation. |
| Contract README | Add canonical files, rules, fixture inventories, and completion commands. |
| Isolated handoff contract | Update inventory counts and preserve the external producer completion gate. |
| `sprint-status.yaml` | Regenerate the stale workspace-specific `story_location`; no status keys change. |

### Technical Impact

This proposal does not authorize production Workflow Commander implementation.
It corrects planning and shared contract evidence before implementation begins.
No new runtime service, database, queue, frontend, core model tool, or user-facing environment variable is introduced.

## 3. Recommended Approach

Use **Direct Adjustment** within the existing epic structure.

The product scope and architecture are still valid.
Rollback provides no benefit because the affected stories remain backlog.
MVP reduction is unnecessary because the identified behaviors are already required by the PRD and NFRs.

### Effort, Risk, And Timeline

- **Effort:** Medium.
- **Risk:** Medium until schema and fixture semantics are agreed; low after validator-backed contracts exist.
- **Timeline impact:** Correct the planning and local contracts before committing affected stories to implementation.
- **External dependency:** Provider-dependent completion remains blocked until the Archon owner supplies real, redacted producer output and it passes compatibility validation.

### Sequencing

1. Approve the story and contract changes in this proposal.
2. Amend `epics.md` acceptance criteria.
3. Harden the gate-decision and operational-diagnostic contract schemas.
4. Add the required local fixture families.
5. Extend the validator and contract documentation.
6. Regenerate sprint metadata from the current workspace without changing backlog state.
7. Obtain and validate real Archon producer evidence.
8. Re-run implementation readiness.

## 4. Detailed Change Proposals

### A. Story Acceptance Criteria

#### Story 2.1c: Manage Project Binding Lifecycle And Status

**Section:** Acceptance Criteria

**OLD:**

```text
- Update preserves binding id, audit history, and validation-state transition.
- Disabled bindings block BMAD or provider actions.
- Status query returns required binding and validation fields.
```

**NEW:**

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

**OLD:**

```text
- Invalid sprint-status input is rejected before mutation.
- A changed story updates the same Project Work Item identity.
- Partial failure returns source provenance.
```

**NEW:**

```text
- Given an enabled Project Binding with a valid Bound Project Cwd and valid `sprint-status.yaml` containing a new epic and story, when materialization runs, then Hermes creates exactly one Project Work Item for each selected BMAD epic or story identity and stores the binding reference, source artifact path, observed BMAD status, and source provenance.
- Given an enabled Project Binding with a valid Bound Project Cwd, when materialization runs, then Hermes reads `sprint-status.yaml` only from that cwd and rejects missing, malformed, or unsupported data before mutation.
- Given the same unchanged BMAD epic or story is materialized again, when Hermes derives its identity, then Hermes reuses the existing Project Work Item, performs an idempotent no-op or provenance refresh, and creates no duplicate Project Work Item or Phase Task.
- Given a BMAD story changes in `sprint-status.yaml`, when materialization runs again, then Hermes derives the same Project Work Item identity and updates the existing item without including phase kind in the identity.
- Given Hermes runtime state has advanced after materialization, when `sprint-status.yaml` is read again, then Hermes records the observed BMAD planning state without treating it as the runtime queue or overwriting Hermes-owned Kanban, gate, workflow, or next-action state.
- Given materialization partially fails after validation begins, when Hermes reports the failure, then provenance identifies affected binding, source file, epic, story, or Project Work Item.
```

**Rationale:** FR-5 requires initial creation, idempotency, provenance, and separation between BMAD planning state and Hermes runtime state.

#### Story 4.1: Run Story Workflow

**Section:** Acceptance Criteria

**OLD:**

```text
- Starting the combined workflow records its run reference.
- Status is available without the provider dashboard.
```

**NEW:**

```text
- Given a Project Work Item has a Phase Task, when the user starts the story workflow from Hermes, then Hermes starts the configured combined story workflow and records the workflow run reference on the Phase Task.
- Given the combined workflow is running, when status is checked from Hermes, then Hermes returns structured workflow progress without requiring the provider dashboard.
- Given the provider-controlled combined workflow advances from story creation through implementation, fix loop, and review, when intermediate phases complete, then Hermes records progress without creating a Hermes-side pause or human gate before provider completion evidence triggers Done Verification.
```

**Rationale:** FR-12 explicitly forbids a Hermes-side pause between combined workflow phases.

#### Story 4.3: Capture Human Gate Decisions And Evidence

**Section:** Acceptance Criteria insertion after provider command association

**OLD:**

```text
- A required provider command result is recorded separately from the human decision record.
```

**NEW:**

```text
- Given a gate decision requires a provider approval, rejection, resume, or retry command, when Hermes records the human decision, then Hermes sends the matching command through the strict provider adapter and records the command result separately from the human decision record.
- Given Hermes receives the same authorized gate decision id or idempotency key more than once, when decision processing is replayed, then Hermes returns the original persisted decision outcome, applies exactly one phase transition, and does not send a duplicate provider control command.
```

**Rationale:** NFR-4 and the story's blocking behavior require replay-safe decisions, but replay behavior is not currently testable.

#### Story 5.2a: Reconcile BMAD Materialization Drift

**Section:** Acceptance Criteria

**OLD:**

```text
- Changed BMAD story state updates existing project work without duplication.
- Deterministic repair evidence is returned through history or diagnostics.
```

**NEW:**

```text
- Given BMAD story artifact state changes after materialization, when reconciliation runs, then Hermes detects whether the Project Work Item needs update without duplicating Project Work Items or Phase Tasks.
- Given BMAD source state is missing or malformed, when reconciliation runs, then Hermes preserves the last known Hermes runtime state, records a source-linked diagnostic, and applies no Project Work Item, Phase Task, gate, or workflow mutation.
- Given BMAD source state is unchanged, when reconciliation runs repeatedly, then Hermes records an idempotent no-op or observation result and creates no duplicate Project Work Item, Phase Task, gate, workflow reference, or history transition.
- Given deterministic repair is applied more than once for the same source version, when reconciliation repeats, then Hermes reuses the original identities and repair result without duplicate mutation.
- Given reconciliation performs deterministic repair, when Story Status History or diagnostics are queried, then Hermes returns what was repaired, why it was deterministic, and which BMAD source records supported it.
```

**Rationale:** The story's own completion gate names missing, malformed, unchanged, changed, and duplicate-safe cases, but its criteria cover only changed state.

#### Story 5.2c: Reconcile Workflow Event Delivery Evidence

**Section:** Acceptance Criteria

**OLD:**

```text
- Duplicated, delayed, terminally failed, or absent delivery is classified without duplicate mutation.
```

**NEW:**

```text
- Given event delivery is duplicated, delayed, terminally failed, or absent after provider completion, when reconciliation evaluates evidence, then Hermes links evidence to the affected workflow run and records the delivery-drift category without duplicate mutation.
- Given the gateway is unavailable while provider workflow state advances, when the gateway returns and reconciliation compares provider state, delivery health, and persisted event receipts, then Hermes classifies missed delivery, projects only deterministic state, preserves idempotency, and creates no duplicate workflow reference, Phase Task transition, gate, comment, or Story Status History entry.
```

**Rationale:** NFR-2 explicitly names gateway downtime as a required reconciliation scenario.

#### Story 5.3c: Resolve Diagnostics And Preserve Audit History

**Section:** Acceptance Criteria

**OLD:**

```text
- Successful resolution records source, timestamp, recovery action, and resulting state while preserving prior history.
```

**NEW:**

```text
- Given a diagnostic has been resolved, when reconciliation or authorized action clears the issue, then Hermes records resolution source, timestamp, recovery action, and resulting state while keeping prior diagnostic history available for audit.
- Given a recovery command fails, returns incompatible output, or cannot prove resolution, when Hermes records the recovery attempt, then Hermes keeps the diagnostic active, appends the failed attempt with redacted command evidence and timestamp, and preserves all prior diagnostic history without reporting the issue as resolved.
```

**Rationale:** The story currently tests only successful resolution and can lose the audit contract on failed recovery.

### B. Gate Decision Contracts

**Current state:** `gate-decision-record.schema.json` exists but is not required by the validator and has no examples.

**Proposed changes:**

1. Add the gate-decision record schema to `REQUIRED_SCHEMA_FILES`.
2. Require an idempotency key or explicitly define `decisionId` as the replay key.
3. Add conditional validation so rejection requires a reason and non-`none` recovery action, while approval produces the allowed completed phase state.
4. Preserve separate human-decision and provider-command evidence through an optional command action plus correlation reference.
5. Add a small gate-decision behavior-case schema for pending, approved, rejected, replayed, and provider-command-failure expectations where a single persisted record cannot express the behavior.
6. Add fixtures for approval, rejection with each recovery route, delayed pending state, replayed approval, and provider-command failure association.
7. Validate that replay produces one decision record, one phase transition, and at most one provider command.

**Rationale:** A record-only schema cannot prove NFR-4 replay safety or the delayed-decision behavior required by Story 4.3.

### C. Operational Diagnostic Contracts

**Current state:** `operational-diagnostic.schema.json` exists but is not required by the validator, has no examples, and does not contain every field promised by Story 5.3a.

**Proposed changes:**

1. Add the operational-diagnostic schema to `REQUIRED_SCHEMA_FILES`.
2. Add required diagnostic `family`, `state`, source provenance, evidence references, and immutable resolution-attempt history.
3. Add `external_delay` to next-action ownership and align recovery vocabulary with the diagnostic family matrix.
4. Preserve redaction-before-persistence as an explicit record invariant.
5. Add fixtures for configuration, decision, external-delay, implementation-defect, duplicate-event, outbox, stale-PR, and unresolved-gate families.
6. Add resolved and failed-recovery fixtures proving append-only history and active-state preservation on failure.
7. Validate every diagnostic family, owner, recovery option, state transition, provenance value, and redaction invariant.

**Rationale:** The current schema cannot fully represent the diagnostic record that Stories 5.3a through 5.3c require.

### D. Contract Validator And Documentation

**OLD:**

```text
The validator requires seven schemas and seven existing fixture families.
The README omits gate-decision and operational-diagnostic contracts.
```

**NEW:**

```text
The validator requires every canonical schema and all local fixture families, prints explicit gate-decision and operational-diagnostic counts, rejects unexpected examples, and validates behavior invariants for replay, redaction, provenance, and immutable recovery history.
The README lists every canonical schema and fixture family and explains local fixture readiness separately from external producer compatibility.
```

Add an explicit external evidence mode to the validator, such as `--archon-evidence <path>` with a completion-gate option that fails when required producer families are absent.
Normal local contract validation must remain deterministic and must not fabricate or silently treat local fixtures as producer evidence.
Captured evidence must be redacted and must never contain raw secrets, raw event signatures, or unsafe command output.

### E. Architecture And Isolated Handoff Documentation

Update `architecture.md` and `cross-project-isolated-handoff-contract.md` to state:

- The total canonical schema count after correction.
- The gate-decision and operational-diagnostic fixture counts.
- The distinction between local fixture validation and external Archon producer compatibility.
- The exact external evidence completion command and ownership.

No architecture decision, product boundary, runtime component, or UI scope changes.

### F. Sprint Tracker

Regenerate `_bmad-output/implementation-artifacts/sprint-status.yaml` from the current checkout so `story_location` no longer points to `/Users/agent/.archon/...`.
Preserve every epic and story status as `backlog` and every retrospective as `optional`.
No IDs are added, removed, or renumbered.

## 5. Implementation Handoff

### Scope Classification

**Moderate** — Product Owner and Developer coordination is required for backlog text, shared contracts, validator behavior, and external provider evidence.
No Product Manager or Solution Architect replan is required unless contract hardening reveals a fundamental cross-project incompatibility.

### Product Owner Responsibilities

- Apply the approved acceptance criteria to the seven affected stories.
- Preserve all existing FR/NFR traceability, story IDs, dependency direction, and headless scope.
- Keep affected stories in backlog until their corrected criteria and local evidence gates are present.

### Hermes Developer Responsibilities

- Harden the local gate-decision and operational-diagnostic schemas.
- Add required local fixture families and validator invariants.
- Update contract README, architecture reality statements, isolated handoff inventory, and sprint metadata.
- Run the local validator from the supported project runtime.
- Do not mark provider-dependent stories done from local fixtures alone.

### Archon Producer Responsibilities

- Capture redacted runtime output for provider binding lifecycle, workflow commands, workflow events, and delivery/outbox status.
- Supply output without secrets, raw signatures, or unredacted command content.
- Validate each captured family against the shared contract package.
- Resolve producer/consumer incompatibilities before provider-dependent Hermes story completion.

### Success Criteria

- `epics.md` contains the seven approved acceptance-criteria corrections.
- Every canonical schema is required and validated.
- Gate-decision and operational-diagnostic fixture families exist, are counted, and pass validation.
- Gate replay, delayed decisions, diagnostic redaction, all diagnostic families, successful resolution, and failed recovery are validated.
- The contract README and architecture report the actual package inventory accurately.
- Sprint metadata points to the current workspace and retains unchanged backlog state.
- Real Archon producer evidence is captured and passes the explicit external evidence validation mode.
- A fresh implementation-readiness assessment reports no critical evidence blockers or story acceptance gaps.

## 6. Checklist Summary

| Checklist Area | Status | Finding |
| --- | --- | --- |
| Trigger and context | Done | Readiness report and filesystem evidence establish the change. |
| Epic impact | Done | Existing epics remain valid; seven stories need criteria changes. |
| Artifact conflict analysis | Done | PRD and UX remain unchanged; epics, contracts, validator, architecture truth statements, and sprint metadata need correction. |
| Path forward | Done | Direct Adjustment is preferred over rollback or MVP reduction. |
| Proposal components | Done | Detailed changes, sequencing, ownership, and success criteria are defined. |
| User approval | Pending | Batch proposal requires explicit review and approval. |
| Sprint status restructuring | Not applicable | No story or epic IDs change. |
| Handoff | Pending approval | Route to Product Owner, Hermes Developer, and Archon producer owner after approval. |

## 7. Approval Decision

Kevin explicitly approved this Sprint Change Proposal on 2026-07-12 after batch review.
Approval authorizes the documented planning, contract, validator, documentation, and sprint-metadata corrections.
Approval does not authorize fabricated external evidence or provider-dependent completion claims.

## 8. Workflow Execution And Handoff Log

| Field | Recorded Outcome |
| --- | --- |
| Issue addressed | Workflow Commander readiness failure caused by three evidence blockers and seven story acceptance gaps. |
| Change scope | Moderate. |
| Artifacts proposed for modification | `epics.md`, `architecture.md`, contract schemas, contract examples, `validate_contracts.py`, contract README, isolated handoff contract, and `sprint-status.yaml`. |
| Artifacts intentionally unchanged | `prd.md` and `ux-headless-interaction-contract.md`. |
| Routed to | Product Owner, Hermes Developer, and Archon producer owner. |
| Product Owner handoff | Apply the seven approved story acceptance-criteria corrections while preserving IDs, ordering, and traceability. |
| Hermes Developer handoff | Harden schemas, add fixtures, extend validation, update inventories, and regenerate sprint metadata. |
| Archon producer handoff | Supply redacted runtime evidence and validate producer compatibility. |
| Completion gate | Re-run implementation readiness only after local contract evidence and external producer evidence are present and validated. |
| Approval | Explicitly approved by kevin on 2026-07-12. |

### Checklist Completion

- `[x]` Trigger and context established with concrete evidence.
- `[x]` Epic and story impact assessed.
- `[x]` PRD, architecture, UX, contract, documentation, and sprint impacts assessed.
- `[x]` Direct Adjustment selected over rollback or MVP reduction.
- `[x]` Detailed before/after story proposals documented.
- `[x]` Contract and validator corrections documented.
- `[x]` Explicit user approval obtained.
- `[N/A]` Sprint status restructuring is unnecessary because no epic or story IDs change.
- `[x]` Handoff roles, sequence, and success criteria confirmed.
