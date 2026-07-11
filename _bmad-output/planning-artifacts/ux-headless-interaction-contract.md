---
title: Headless UX Interaction Contract - Hermes Agent Workflow Commander
status: handoff
created: '2026-07-12'
updated: '2026-07-12'
source: derived from local PRD, architecture, and epics headless interaction requirements
---

# Headless UX Interaction Contract

## Scope

Workflow Commander v1 is a headless operator experience.
The user experience is delivered through Hermes commands, agent interactions, structured command or API results, durable records, Story Status History, diagnostics, and optional existing notification transports.
This artifact does not authorize a dedicated dashboard, graphical Kanban board, gate screen, timeline screen, desktop view, web application, or marketing surface.

## Primary Interaction Patterns

| Interaction | User Need | Required Response Shape |
| --- | --- | --- |
| Project Binding inspection | Know which project Hermes will operate on | Active binding identity, profile, Bound Project Cwd, GitHub reference, BMAD mount status, provider binding state, and conflicts |
| BMAD workflow invocation | Run planning from the intended project | Workflow name, cwd used, produced artifact paths, result state, failure diagnostics, and preserved Project Binding context |
| Provider workflow control | Start, inspect, approve, reject, resume, retry, or cancel without provider dashboard use | Provider, command, correlation id, parsed result, stdout/stderr references when safe, timeout or failure state, and cwd when applicable |
| Done Verification Gate | Decide whether implementation evidence is actually done | Gate kind, evidence references, provider run reference, GitHub reference when present, decision options, actor, timestamp, and reason when supplied |
| Story Status History | Understand why a story changed state | Source-labeled BMAD, Hermes, provider, workflow event, GitHub, gate, reconciliation, and next-action entries |
| Operational diagnostics | Recover from orchestration problems safely | Category, family, severity, affected references, redacted evidence, owner, recovery option, timestamp, state, and source provenance |

## Headless Usability Requirements

- Every blocked action returns the responsible domain and a recovery option instead of only a stack trace.
- Next actions use human-facing workflow language and identify the owner as user action, configuration action, Hermes automation, provider action, BMAD action, GitHub action, implementation-agent action, or external delay.
- Gate decisions remain explicit human actions and are never inferred from GitHub merge state or favorable provider completion alone.
- Structured results preserve machine-readable fields for automation and enough human-readable context for command-line or notification review.
- Secrets, raw signatures, and unsafe command output are redacted from command logs, event logs, diagnostics, gate evidence, and Story Status History.
- Notification mirrors may surface pending gate or diagnostic state, but durable Hermes records remain the source of truth for decisions and recovery.

## Validation Expectations

- Story acceptance criteria that expose command or API results must prove the required response fields are present.
- Story Status History tests must show source labels and next action without requiring a graphical timeline.
- Gate tests must show approval, rejection, and recovery routing through authorized command or agent interaction.
- Diagnostic tests must cover the diagnostic family matrix in `epics.md` and prove redaction before persistence or return.
