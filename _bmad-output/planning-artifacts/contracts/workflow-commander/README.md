# Workflow Commander Shared Contract Package

Status: local contract handoff generated on 2026-07-09.
This folder is the required local planning path for shared Hermes Agent Workflow Commander schemas and examples.
Producer and consumer implementation stories may reference this package for story readiness once their story-specific fixtures and compatibility tests are present.
Runtime implementation remains separately gated by Archon and Hermes code changes that validate against these contracts.

## Required Schemas

- `schemas/workflow-command-envelope.schema.json`
- `schemas/workflow-event-envelope.schema.json`
- `schemas/workflow-provider-binding.schema.json`
- `schemas/workflow-delivery-status.schema.json`
- `schemas/project-work-identity.schema.json`
- `schemas/phase-task-identity.schema.json`
- `schemas/operational-diagnostic.schema.json`
- `schemas/gate-decision-record.schema.json`

## Required Provider Command Examples

- `examples/providers/archon/commands/start-success.json`
- `examples/providers/archon/commands/status-success.json`
- `examples/providers/archon/commands/approve-success.json`
- `examples/providers/archon/commands/reject-success.json`
- `examples/providers/archon/commands/resume-success.json`
- `examples/providers/archon/commands/retry-success.json`
- `examples/providers/archon/commands/cancel-success.json`
- `examples/providers/archon/commands/error-malformed-request.json`

## Required Workflow Event Examples

- `examples/workflow-events/workflow-completed.json`
- `examples/workflow-events/workflow-failed.json`
- `examples/workflow-events/approval-requested.json`
- `examples/workflow-events/delivery-failed.json`
- `examples/workflow-events/artifact-event.json`

## Required Archon Provider Event Examples

- `examples/providers/archon/events/workflow-completed.json`
- `examples/providers/archon/events/workflow-failed.json`
- `examples/providers/archon/events/approval-requested.json`
- `examples/providers/archon/events/delivery-failed.json`
- `examples/providers/archon/events/artifact-event.json`

## Required Callback Rejection Examples

- `examples/callback-rejections/bad-signature.json`
- `examples/callback-rejections/stale-timestamp.json`
- `examples/callback-rejections/duplicate-event-id.json`
- `examples/callback-rejections/wrong-binding.json`
- `examples/callback-rejections/unknown-project.json`
- `examples/callback-rejections/schema-mismatch.json`
- `examples/callback-rejections/wrong-profile-secret.json`

## Required Materialization Examples

- `examples/materialization/new-story.json`
- `examples/materialization/unchanged-story.json`
- `examples/materialization/changed-story.json`
- `examples/materialization/missing-sprint-status.json`
- `examples/materialization/malformed-sprint-status.json`
- `examples/materialization/duplicate-phase-task-prevention.json`

## Additional Archon Verification Examples

- `examples/providers/archon/bindings/status-valid.json`
- `examples/providers/archon/bindings/status-conflicting.json`
- `examples/providers/archon/delivery-status/healthy.json`
- `examples/providers/archon/delivery-status/terminal-failure.json`

## Diagnostic And Gate Decision Examples

- `examples/diagnostics/binding-conflict.json`
- `examples/diagnostics/unresolved-completion-evidence.json`
- `examples/gate-decisions/approve-done-verification.json`
- `examples/gate-decisions/reject-rerun-fix-loop.json`

## Readiness Rule

Archon producer stories that emit provider command, workflow event, provider binding, or delivery-health payloads must validate against the relevant fixtures.
Hermes consumer stories that parse provider command, workflow event, provider binding, delivery-health, materialization, phase-task, gate, or reconciliation payloads must validate against the same fixtures.
The first implementation slice should create tests that load these schemas and examples from this directory instead of duplicating the shapes inline.
If a story changes a schema or enum, update the schema, every affected example, and the story's contract reference in the same change.
