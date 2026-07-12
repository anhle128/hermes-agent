# Sprint Change Proposal: Workflow Commander Readiness Corrections

**Date:** 2026-07-09
**Project:** hermes-agent
**Requested by:** kevin
**Change trigger:** `implementation-readiness-report-2026-07-09.md` marked the handoff `NOT READY`.
**Mode:** Batch direct correction, based on the user request to find the report issues and fix them.

## 1. Issue Summary

The implementation-readiness report found that the Hermes Agent Workflow Commander planning set had complete FR coverage but was not ready for Phase 4 implementation.
The critical blocker was missing local shared contract fixtures for workflow command envelopes, workflow events, provider binding shape, Project Work Item identity, Phase Task identity, callback rejection cases, materialization idempotency, and duplicate/rejection scenarios.
The report also found incomplete explicit NFR traceability, unresolved producer-side Archon verification inputs, guarded stories that needed pre-sprint slicing disposition, and qualitative terms such as "user-actionable diagnostic" without a concrete vocabulary contract.

## 2. Impact Analysis

**Epic impact:** Epics 2 through 5 remain valid and still cover all 17 PRD functional requirements.
The change does not alter MVP scope.
It changes readiness gates and adds the contract package needed before implementation stories can be pulled.

**Story impact:** Stories 2.5, 2.6, 3.2, 3.4a, 3.4b, 3.4c, 3.6a, 3.6b, 3.6c, 3.8, 4.2, 4.3, 5.1, 5.2a, 5.2b, 5.2c, and 5.3 now have concrete local contract fixtures or vocabulary to reference.
Stories 2.1, 3.6c, 5.2b, and 5.3 keep their sprint-slicing guard and now have explicit pre-sprint split guidance.

**Artifact conflicts:** `epics.md` and `architecture.md` previously said the shared contract fixtures did not exist.
Those statements conflicted with the corrected local contract package and were updated.

**Technical impact:** No runtime code changed.
Future implementation tests must load schemas and examples from `_bmad-output/planning-artifacts/contracts/workflow-commander/` instead of duplicating contract shapes inline.

## 3. Recommended Approach

Use **Direct Adjustment**.
The planning artifacts were internally coherent, so rollback or MVP reduction was not justified.
The correct fix was to generate the missing local contract handoff, add traceability and slicing gates, and update architecture readiness language.

**Effort:** Medium planning-artifact update.
**Risk:** Low for runtime behavior because no executable code changed.
**Timeline impact:** Removes the local fixture-presence blocker, but implementation readiness still requires story-specific tests and Archon producer compatibility proof.

## 4. Detailed Change Proposals

### Contract Package

OLD:

```text
No local hermes-agent Workflow Commander contract package existed.
The parent and Archon contract folders contained README placeholders only.
```

NEW:

```text
Added _bmad-output/planning-artifacts/contracts/workflow-commander/ with schemas and examples for command envelopes, event envelopes, provider bindings, delivery status, identities, diagnostics, gate decisions, callback rejections, Archon commands/events, and materialization.
```

Rationale: Implementation agents need local machine-readable fixtures before they can validate provider adapters, event ingress, materialization, diagnostics, and gate behavior.

### Epics

OLD:

```text
every story references shared contract fixtures ... those fixtures do not exist yet
```

NEW:

```text
the shared Workflow Commander contract package now exists in _bmad-output/planning-artifacts/contracts/workflow-commander/ as of 2026-07-09
```

Rationale: The local missing-fixture blocker is resolved, while story readiness remains gated by tests that load the exact fixtures and prove Archon compatibility where needed.

Added an explicit NFR coverage map for NFR-1 through NFR-17.
Added guarded-story slicing disposition for Stories 2.1, 3.6c, 5.2b, and 5.3.
Updated story dependencies that referenced blocked parent fixtures so they now point to the local contract package.

### Architecture

OLD:

```text
Implementation starts with shared examples/schemas ... these do not exist yet as of this handoff.
```

NEW:

```text
The local Hermes handoff package now exists at _bmad-output/planning-artifacts/contracts/workflow-commander/.
Implementation stories still need compatibility tests that load these artifacts before they can be marked ready.
```

Rationale: Architecture should reflect the corrected contract state without overstating runtime implementation readiness.

Also updated the stack table to `hermes-agent` version `0.18.0`, matching `pyproject.toml`.

### PRD

No PRD scope change was required.
The PRD already defines the correct FR/NFR set and anti-goals.

## 5. Checklist Summary

| Checklist Area | Status | Finding |
| --- | --- | --- |
| Trigger and context | Done | Readiness report identified missing contracts and traceability gaps. |
| Epic impact | Done | Epics remain valid; readiness gates changed. |
| Artifact conflict analysis | Done | `epics.md` and `architecture.md` had stale missing-fixture statements. |
| Path forward | Done | Direct Adjustment selected. |
| Proposal components | Done | Contract package, NFR map, slicing disposition, and architecture readiness text added. |
| Final handoff | Done | Future implementation must validate against local fixtures and Archon producer outputs. |

## 6. Implementation Handoff

**Scope classification:** Moderate planning correction.

**Developer agent responsibilities:**

- Use `_bmad-output/planning-artifacts/contracts/workflow-commander/` as the source of truth for initial Workflow Commander contract tests.
- Do not inline duplicate schemas when implementing provider adapters, event ingress, materialization, diagnostics, or gates.
- Keep Project Binding, BMAD artifacts, provider state, GitHub state, and Hermes Project Work state as separate sources.

**PO/DEV responsibilities before sprint commitment:**

- Split Stories 2.1, 3.6c, 5.2b, and 5.3 when one-cycle completion evidence is not available.
- Confirm Archon producer stories emit command JSON, signed events, binding status, and delivery health compatible with the local fixtures.

**Success criteria:**

- All JSON schemas and examples parse successfully.
- Each implementation story that consumes a fixture has a focused compatibility test.
- Provider-facing stories are not marked complete until Archon producer outputs validate against the same contracts.
