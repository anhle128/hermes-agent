# Sprint Change Proposal: Workflow Commander Readiness Corrections

**Date:** 2026-07-12
**Project:** hermes-agent
**Requested by:** kevin
**Change trigger:** `implementation-readiness-report-2026-07-12.md` marked the handoff `NOT READY`.
**Mode:** Automated batch correction. User approval for in-scope planning-artifact corrections was supplied by the workflow invocation.

## 1. Issue Summary

The latest readiness evaluator found three implementation-readiness issues:

1. Critical: `_bmad-output/implementation-artifacts/sprint-status.yaml` was stale. It tracked 22 older/composite story keys while `_bmad-output/planning-artifacts/epics.md` defines 30 current Hermes-owned stories.
2. Major: provider-dependent Hermes stories still depend on compatible Archon producer output that has not been proven in this local handoff.
3. Minor: Story 2.3 carried one acceptance criterion about future real-provider cwd validation that belongs with Story 3.4a.

The trigger is a planning and handoff consistency problem, not a change to Workflow Commander MVP scope.

## 2. Impact Analysis

**Epic impact:** Epics 2 through 5 remain valid. No epic is removed, added, renumbered, or resequenced.

**Story impact:** The implementation tracker now mirrors the 30 story headings in `epics.md`. Story 2.3 is narrowed to generic cwd enforcement and the minimal provider-action test double. Story 3.4a now owns the real provider-adapter cwd validation criterion.

**Artifact conflicts:** The stale tracker could cause non-interactive automation to pick obsolete or collapsed story keys. The correction regenerates the tracker from the current epics and preserves all story statuses as `backlog`.

**Technical impact:** No production code changed. Provider-dependent stories remain completion-gated by validated Archon producer output. The tracker schema does not define a `blocked` story status, so dependency blocking remains in the story dependency records and tracker notes rather than an unsupported status value.

## 3. Recommended Approach

Use **Direct Adjustment**.

The readiness findings can be resolved by updating planning artifacts in place:

- Regenerate the sprint tracker from the current epics.
- Preserve explicit Archon dependency records and prevent completion claims from local fixtures alone.
- Move the future-provider cwd validation criterion to the story that introduces the real provider adapter.

Rollback and MVP review are not justified because the PRD, architecture, epics, UX contract, and local contract package are otherwise aligned.

**Effort:** Low planning correction.
**Risk:** Low. The changes affect planning/tracking artifacts only.
**Timeline impact:** Removes the queue mismatch that blocks story automation. Provider-dependent completion remains gated until compatible Archon producer output is validated.

## 4. Detailed Change Proposals

### Sprint Status Tracker

OLD:

```text
_bmad-output/implementation-artifacts/sprint-status.yaml tracked 22 older/composite story keys generated on 2026-07-09.
Examples included 2-1-create-and-validate-project-bindings, 3-6c-map-accepted-workflow-events-to-project-work, and 5-3-surface-operational-diagnostics-and-recovery-paths.
```

NEW:

```text
_bmad-output/implementation-artifacts/sprint-status.yaml tracks all 30 current story keys from epics.md, including:
- 2.1a, 2.1b, 2.1c
- 3.6d and 3.6e
- 5.2b through 5.2e
- 5.3a through 5.3c
```

Rationale: Non-interactive story creation and implementation workflows must resolve the same story queue that `epics.md` defines.

### Provider-Dependent Story Completion Gate

OLD:

```text
Provider-dependent stories could be misread as locally complete because the local contract package validates.
```

NEW:

```text
The tracker keeps provider-dependent stories in backlog, and the tracker notes state that Archon-dependent Hermes stories must not be marked done from local fixtures alone.
Existing epics dependency records are preserved until compatible Archon producer output is available and validated.
```

Rationale: Local fixtures support Hermes-side implementation, but they do not prove the external Archon producer output.

### Story 2.3 And Story 3.4a

OLD:

```text
Story 2.3 included a future-story acceptance criterion requiring Story 3.4a to reuse the cwd guard with the real provider adapter.
```

NEW:

```text
Story 2.3 now keeps only generic cwd enforcement and minimal provider-action test-double validation.
Story 3.4a now includes the real provider-adapter cwd validation criterion.
```

Rationale: The real provider adapter is introduced in Epic 3, so adapter-specific validation belongs in Story 3.4a while Story 2.3 remains independently implementable.

## 5. Checklist Summary

| Checklist Area | Status | Finding |
| --- | --- | --- |
| Trigger and context | Done | Latest readiness report supplied the trigger and evidence. |
| Epic impact | Done | Epics remain valid; no resequencing or scope reduction required. |
| Artifact conflict analysis | Done | `sprint-status.yaml` was the only stale artifact requiring regeneration. |
| Path forward | Done | Direct Adjustment selected. |
| Proposal components | Done | Specific tracker and story-text edits are captured above. |
| Final handoff | Done with external caveat | Provider-dependent stories remain gated by compatible Archon producer output. |

## 6. Implementation Handoff

**Scope classification:** Minor planning correction.

**Developer agent responsibilities:**

- Use `_bmad-output/implementation-artifacts/sprint-status.yaml` as the current implementation tracker.
- Do not mark provider-dependent Hermes stories done from local fixtures alone.
- Validate compatible Archon producer output before completion claims for provider-dependent stories.
- Implement Story 2.3 without requiring the real Archon adapter.
- Implement Story 3.4a with real provider-adapter cwd validation.

**Success criteria:**

- The tracker contains 30 current story keys from `epics.md`.
- Obsolete/composite tracker keys are removed.
- Story 2.3 has no future-provider acceptance criterion.
- Story 3.4a owns real adapter cwd validation.
- Provider-dependent completion gating remains explicit and unsupported external evidence is not invented.
