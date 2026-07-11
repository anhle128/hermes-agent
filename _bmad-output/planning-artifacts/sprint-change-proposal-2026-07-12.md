# Sprint Change Proposal: Workflow Commander Readiness Corrections

**Date:** 2026-07-12
**Project:** hermes-agent
**Requested by:** kevin
**Change trigger:** `implementation-readiness-report-2026-07-12.md` marked the handoff `NOT READY`.
**Mode:** Automated batch correction with user approval supplied by the workflow invocation.

## 1. Issue Summary

The latest readiness result found the Workflow Commander planning handoff not ready because one configured persistent fact was missing and several local planning artifacts disagreed about contract readiness, NFR numbering, and story quality.
The report also recorded two minor concerns: no UX artifact existed for the headless operator experience, and external Archon producer completion status was not locally proven.

## 2. Impact Analysis

**Epic impact:** Epics 2 through 5 remain valid and no MVP scope reduction is required.
The correction updates readiness gates and story wording, but does not add runtime scope or a graphical frontend.

**Story impact:** Story 2.3 is narrowed so it owns generic cwd enforcement and a minimal provider-action cwd test double, while real Archon adapter cwd validation remains with Story 3.4a.
Story 5.3a is strengthened with an explicit diagnostic family matrix and additional persistence/redaction/idempotency acceptance criteria.

**Artifact conflicts:** `architecture.md` and the contract package now agree that 65 examples exist and validate through the repository Python path.
`prd.md` and `epics.md` now use matching NFR-1 through NFR-17 identifiers.
The missing `cross-project-isolated-handoff-contract.md` persistent fact has been restored from local planning facts.

**Technical impact:** No production code changed.
Future implementation work should use `uv run python _bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py` for contract validation.

## 3. Recommended Approach

Use **Direct Adjustment**.
The readiness issues were local artifact consistency and story-quality defects, not evidence that the Workflow Commander MVP or epic sequence is wrong.
Rollback and MVP review are not justified.

**Effort:** Medium planning-artifact correction.
**Risk:** Low for runtime behavior because the change is documentation and planning only.
**Timeline impact:** Removes local readiness blockers for the handoff package, except for external Archon producer completion evidence that is not available in this worktree.

## 4. Detailed Change Proposals

### Persistent Fact

OLD:

```text
_bmad-output/planning-artifacts/cross-project-isolated-handoff-contract.md was configured as a persistent fact but did not exist.
```

NEW:

```text
Added the missing file with isolated-handoff rules, ownership boundaries, local contract package state, validation command, and external Archon dependency caveat.
```

Rationale: Readiness workflows need this fact to validate isolated implementation without reading parent planning files.

### PRD NFRs

OLD:

```text
The PRD listed 16 unlabeled NFR bullets.
The epics NFR coverage map referenced NFR-1 through NFR-17.
```

NEW:

```text
The PRD now labels NFR-1 through NFR-17 and includes NFR-15 for dependency records and bounded ownership.
```

Rationale: Implementation agents need stable NFR ids that match the epics traceability map.

### Architecture And Contract Validation

OLD:

```text
Architecture said no example fixtures were observed.
The contract README instructed bare python3 validation.
```

NEW:

```text
Architecture records the current 65-example fixture inventory and uses uv run python for validation.
The contract README now uses the same supported Python resolution path.
```

Rationale: The local package validates with CPython 3.11 through `uv`; system `python3` may be too old for this repository.

### Story 2.3

OLD:

```text
Story 2.3 required proving provider adapter calls receive the Bound Project Cwd, even though real provider adapters are introduced in Epic 3.
```

NEW:

```text
Story 2.3 now proves cwd propagation through BMAD actions and a minimal provider-action cwd test double.
Story 3.4a remains responsible for real Archon provider adapter cwd validation.
```

Rationale: This removes forward-coupling while preserving FR-3 cwd safety.

### Story 5.3a

OLD:

```text
Story 5.3a had two broad acceptance criteria for a wide diagnostic persistence surface.
```

NEW:

```text
Story 5.3a now includes a diagnostic family matrix for configuration, decision, external-delay, implementation-defect, duplicate-event, outbox, stale-PR, and unresolved-gate diagnostics, plus explicit persistence, redaction, duplicate-safe, and completion-conflict acceptance criteria.
```

Rationale: The story is now implementable as a taxonomy and persistence foundation without absorbing query formatting or resolution history.

### UX Artifact

OLD:

```text
No UX artifact existed.
```

NEW:

```text
Added ux-headless-interaction-contract.md to capture command/API/notification interaction expectations for the explicitly headless v1 scope.
```

Rationale: The artifact documents headless UX obligations without authorizing a graphical frontend.

### External Producer Evidence

OLD:

```text
External Archon producer completion status was not locally proven.
```

NEW:

```text
No unsupported producer completion status was invented.
The restored handoff contract states that provider-dependent stories remain externally gated until compatible Archon producer output is available and validated.
```

Rationale: This issue cannot be converted into proof from local Hermes artifacts alone.

## 5. Checklist Summary

| Checklist Area | Status | Finding |
| --- | --- | --- |
| Trigger and context | Done | Readiness report identified the change trigger and evidence. |
| Epic impact | Done | Epics remain valid; no replan or resequencing required. |
| Artifact conflict analysis | Done | PRD, architecture, epics, contract README, missing handoff fact, and UX artifact were corrected. |
| Path forward | Done | Direct Adjustment selected. |
| Proposal components | Done | Specific before/after proposals are captured above. |
| Final handoff | Done with external caveat | Archon producer completion evidence remains external and unclaimed. |

## 6. Implementation Handoff

**Scope classification:** Moderate planning correction.

**Developer agent responsibilities:**

- Use the local PRD, architecture, epics, UX contract, handoff contract, and contract package as the implementation inputs.
- Validate contracts with `uv run python _bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py`.
- Implement Story 2.3 against generic cwd enforcement and the minimal provider-action test double; defer real Archon adapter cwd validation to Story 3.4a.
- Implement Story 5.3a as the diagnostic taxonomy and persistence foundation defined by the matrix.

**PO/DEV responsibilities before provider-dependent story completion:**

- Keep Archon producer dependencies explicit in story dependency records.
- Do not mark provider-dependent stories complete until compatible Archon producer output is available and validates against the local fixtures.

**Success criteria:**

- Readiness workflows can load the restored persistent fact.
- PRD and epics NFR ids remain aligned.
- Architecture and contract README describe the actual local fixture package and supported validation command.
- Story 2.3 and Story 5.3a are implementable without forward-coupling or underspecified acceptance criteria.
