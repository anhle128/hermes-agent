# Sprint Change Proposal: External Archon Producer Evidence Blocker

**Date:** 2026-07-12
**Project:** hermes-agent
**Requested by:** kevin
**Change trigger:** `implementation-readiness-report-2026-07-12.md` marked the current handoff `NOT READY`.
**Mode:** Automated batch correction. The workflow invocation supplied approval for in-scope planning-artifact corrections.
**Correct Course result:** BLOCKED for missing external Archon producer runtime evidence. No unsupported producer facts were invented.

## 1. Issue Summary

The latest readiness evaluator found one major blocker:

- Required external Archon producer runtime output is absent from the isolated local handoff.

The local PRD, architecture, epics, UX contract, tracker, and local contract fixtures are otherwise aligned. The readiness issue is not a local FR coverage, UX scope, architecture, story-structure, or fixture-validation failure.

The missing evidence is external to the `hermes-agent` local handoff. It must be captured from the Archon producer runtime and validated against the local contract package before provider-dependent Hermes stories can be marked `done`.

## 2. Impact Analysis

**Epic impact:** Epics 2 through 5 remain valid. No epic is added, removed, renumbered, resequenced, or reduced in scope.

**Story impact:** Provider-dependent Hermes stories remain planned, but their completion is blocked until compatible Archon producer output is available and validated. Locally satisfiable stories can proceed where their dependency records allow fixture-driven Hermes-side implementation.

**Artifact conflicts:** No PRD, architecture, UX, or sprint tracker conflict was found in the latest readiness run. The current epics and isolated handoff contract already state the external-evidence blocker, and `sprint-status.yaml` already warns not to mark provider-dependent stories done from local fixtures alone.

**Technical impact:** No production implementation change is authorized by this proposal. The required remediation is evidence capture and validation from the external Archon producer.

## 3. Recommended Approach

Use **Direct Adjustment with an explicit external blocker**.

The supported local correction is to keep the Correct Course proposal aligned with the latest readiness result and preserve the existing local completion gate:

- Keep provider-dependent Hermes stories out of `done` until compatible Archon producer output is supplied and validated.
- Preserve dependency records in `epics.md` for stories that consume parent contract work or Archon producer output.
- Preserve the `sprint-status.yaml` warning that local fixtures alone are insufficient for provider-dependent done claims.
- Do not invent or infer external producer compatibility from local examples.

Rollback is not useful because no completed Hermes implementation work is being corrected. MVP review is not justified because the blocker is missing external evidence, not an invalid product scope.

**Effort:** Low for local planning alignment; external evidence capture effort belongs to the Archon producer side.
**Risk:** Low for local documents; readiness remains blocked until external evidence exists.
**Timeline impact:** Hermes-side implementation may proceed only for stories whose dependencies are locally satisfiable. Provider-dependent done claims remain blocked.

## 4. Detailed Change Proposals

### Sprint Change Proposal

OLD:

```text
The prior proposal referenced findings outside the latest readiness result.
```

NEW:

```text
The proposal now references only the latest readiness finding: missing external Archon producer runtime output.
It records BLOCKED status for external validation and leaves unsupported producer-evidence sections unchanged.
```

Rationale: Correct Course must address only issues identified by the latest `bmad-check-implementation-readiness` result.

### External Evidence Gate

CURRENT:

```text
_bmad-output/planning-artifacts/epics.md, _bmad-output/planning-artifacts/cross-project-isolated-handoff-contract.md,
and _bmad-output/implementation-artifacts/sprint-status.yaml already state that provider-dependent Hermes stories
must not be marked done from local fixtures alone.
```

UNCHANGED:

```text
Those gate records remain unchanged because they already match the latest readiness recommendation.
```

Rationale: The remaining blocker is missing project evidence, not a missing local planning instruction.

## 5. Checklist Summary

| Checklist Area | Status | Finding |
| --- | --- | --- |
| Trigger and context | Done | Latest readiness report supplied the trigger and evidence. |
| Epic impact | Done | Epics remain valid; provider-dependent completion remains externally blocked. |
| Artifact conflict analysis | Done | No PRD, architecture, UX, epics, or tracker conflict found for the latest single-blocker result. |
| Path forward | Done | Direct Adjustment selected for local proposal alignment; external validation remains blocked. |
| Proposal components | Done | Missing facts and handoff responsibilities are listed below. |
| Final handoff | BLOCKED for external validation | Batch-mode approval covers supported local corrections, but external producer output is absent. |

## 6. Implementation Handoff

**Scope classification:** Moderate coordination blocker. Local planning alignment is limited, but readiness cannot pass until external Archon producer evidence is supplied.

**Developer agent responsibilities:**

- Use `_bmad-output/implementation-artifacts/sprint-status.yaml` as the current implementation tracker.
- Do not mark provider-dependent Hermes stories done from local fixtures alone.
- Preserve Archon dependency records in provider-dependent story files.
- Validate compatible external Archon producer output before completion claims for provider-dependent stories.

**Archon producer-side missing facts:**

- Captured Archon provider binding lifecycle output for create, update, status, rotate, disable, and remove paths.
- Captured Archon workflow command output for start, status, approve, reject, resume, retry, cancel, timeout, schema mismatch, malformed request, unexpected exit, and unexpected state paths.
- Captured Archon workflow event output for workflow started, completed, failed, approval requested, delivery failed, artifact recorded, and redelivery paths.
- Captured Archon delivery and outbox status output for healthy, delayed, retrying, failed, duplicated, terminal-failure, and reconciliation-pending paths.

**Success criteria for rerunning readiness:**

- External producer output is present in the isolated handoff or otherwise available to the validator.
- The output validates against `_bmad-output/planning-artifacts/contracts/workflow-commander/`.
- Provider-dependent story completion evidence references validated producer output, not local fixtures alone.
- `bmad-check-implementation-readiness` is rerun after the evidence is added.

## 7. Corrections Applied

| Artifact | Change | Reason |
| --- | --- | --- |
| `_bmad-output/planning-artifacts/sprint-change-proposal-2026-07-12.md` | Refreshed the proposal to match the latest readiness result: one major external Archon producer evidence blocker. | Removes stale prior-run scope and keeps Correct Course limited to the latest readiness issue. |

## 8. Artifacts Reviewed But Left Unchanged

| Artifact | Reason Unchanged |
| --- | --- |
| `_bmad-output/planning-artifacts/epics.md` | Already states the Provider Completion Gate, current external evidence absence, and provider-dependent story dependency records. |
| `_bmad-output/planning-artifacts/cross-project-isolated-handoff-contract.md` | Already lists the External Archon Validation Blocker and the required output families. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Already warns that provider-dependent Hermes stories must not be marked done from local fixtures alone. |
| `_bmad-output/planning-artifacts/prd.md` | No PRD conflict was identified by readiness. |
| `_bmad-output/planning-artifacts/architecture.md` | No architecture conflict was identified by readiness. |
| `_bmad-output/planning-artifacts/ux-headless-interaction-contract.md` | No UX conflict was identified by readiness. |
