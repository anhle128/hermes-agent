# Investigation: Story 2.1a Full Regression Gate

## Hand-off Brief

1. **What happened.** Story 2.1a initially could not move to review because `bash scripts/run_tests.sh` failed even though focused Project Binding tests and lint passed.
2. **Where the case stands.** Resolved. Reproduced blocker clusters were fixed or made environment-aware, and the final full regression passed.
3. **What's needed next.** Human review of Story 2.1a and the regression cleanup diff. No open test blocker remains for this gate.

## Case Info

| Field | Value |
| ----- | ----- |
| Ticket | Story 2.1a |
| Slug | story-2-1a-full-regression-gate |
| Date opened | 2026-07-14 |
| Date resolved | 2026-07-14 |
| Status | Resolved |
| System | Darwin 25.5.0 arm64; Python 3.11.15 |
| Evidence sources | Story file, spec file, sprint status, targeted reruns, full regression output |

## Problem Statement

`bmad-dev-story` could not promote Story 2.1a because the required full regression gate failed outside the Project Binding focused test surface. The focused acceptance run for `tests/project_work/test_bindings.py` and focused lint for `hermes_project_work/bindings.py` / `tests/project_work/test_bindings.py` were already green.

## Evidence Inventory

| Source | Status | Notes |
| ------ | ------ | ----- |
| `_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md` | Updated | Story status is now `review`; Dev Agent Record contains final green evidence. |
| `_bmad-output/implementation-artifacts/spec-2-1a-full-regression-blockers.md` | Updated | Spec status is `done`; Suggested Review Order was appended. |
| `_bmad-output/implementation-artifacts/sprint-status.yaml` | Updated | `2-1a-create-and-persist-project-bindings` moved from `in-progress` to `review`. |
| `bash scripts/run_tests.sh tests/project_work/test_bindings.py -q` | Passed | 132/132 Project Binding tests passed. |
| `.venv/bin/python -m ruff check ...` | Passed | Changed implementation and test files passed lint. |
| Targeted blocker suite | Passed | 31 files, 1,418 tests passed, 0 failed. |
| `bash scripts/run_tests.sh` | Passed | 1,887 files, 39,307 tests passed, 0 failed. |

## Resolution Summary

The full-regression blocker was a set of environment-sensitive and cross-platform assumptions outside the Project Binding package, plus two additional blockers discovered during final gate reruns:

- Darwin keychain credential reads now treat non-object JSON payloads as absent credentials instead of crashing OAuth tests.
- Optional ACP and WeCom validation dependencies are installed in the local venv used by `scripts/run_tests.sh`.
- Darwin `/tmp` canonicalization tests now compare resolved paths where production intentionally resolves paths.
- Systemd-related tests either mock systemd availability for unit-level flows or skip pass-through checks when `systemctl` is absent.
- s6 service event directory mode assertions now account for host setgid clearing while preserving the production chmod behavior.
- Kanban worker SIGTERM test liveness now mirrors production Darwin zombie detection.
- Browser CDP failure messages now distinguish no executable candidate from failed launch attempts and retain manual debugging guidance.
- Shutdown forensics now bounds diagnostics even when GNU `timeout` is unavailable.
- BaseEnvironment snapshot temp files now use `command mktemp` instead of PID-derived names; this was a reproduced full-regression blocker from the first post-fix full rerun, not an unapproved scope expansion.
- Ignore-user-config tests now use a sentinel model name that cannot collide with project-level fallback config.

## Confirmed Findings

### Finding 1: Story-specific validation stayed green

**Evidence:** `bash scripts/run_tests.sh tests/project_work/test_bindings.py -q` passed 132/132, and focused ruff passed.

**Detail:** The Project Binding implementation scope stayed limited to schema, additive migration/repair, create/read operations, restart persistence, and persistence-level uniqueness.

### Finding 2: Initial full-regression failures were outside Project Binding

**Evidence:** Representative reruns traced failures to Anthropic keychain handling, ACP optional dependency availability, file path canonicalization, service/systemd assumptions, TUI browser diagnostics, shutdown forensics, and shell snapshot behavior.

**Detail:** None of the reproduced blocker clusters required broadening `hermes_project_work/bindings.py` beyond Story 2.1a.

### Finding 3: The full regression gate now passes

**Evidence:** `bash scripts/run_tests.sh` completed with 1,887 files, 39,307 tests passed, and 0 failed.

**Detail:** The story and sprint status can move to `review` because the completion gate is no longer blocked.

## Final Validation

- `bash scripts/run_tests.sh tests/project_work/test_bindings.py -q` -- passed: 132/132.
- `.venv/bin/python -m ruff check agent/anthropic_adapter.py gateway/shutdown_forensics.py hermes_cli/browser_connect.py hermes_cli/service_manager.py hermes_project_work/bindings.py tools/environments/base.py tests/agent/test_anthropic_keychain.py tests/agent/test_anthropic_output_field_leak.py tests/cli/test_cli_browser_connect.py tests/gateway/test_background_command.py tests/gateway/test_shutdown_forensics.py tests/hermes_cli/test_gateway_service.py tests/hermes_cli/test_gateway_wsl.py tests/hermes_cli/test_ignore_user_config_flags.py tests/hermes_cli/test_service_manager.py tests/hermes_cli/test_signal_handler_kanban_worker.py tests/project_work/test_bindings.py tests/test_live_system_guard_self_test.py tests/test_tui_gateway_server.py tests/tools/test_base_environment.py tests/tools/test_file_tools.py tui_gateway/server.py` -- passed.
- `bash scripts/run_tests.sh tests/agent/test_anthropic_keychain.py tests/gateway/test_shutdown_forensics.py tests/cli/test_cli_browser_connect.py tests/test_tui_gateway_server.py tests/tools/test_base_environment.py -q` -- passed: 5 files, 406 tests.
- `bash scripts/run_tests.sh tests/agent/test_anthropic_adapter.py tests/agent/test_anthropic_keychain.py tests/agent/test_anthropic_output_field_leak.py tests/acp tests/cli/test_cli_browser_connect.py tests/gateway/test_background_command.py tests/gateway/test_shutdown_forensics.py tests/gateway/test_wecom_callback.py tests/hermes_cli/test_gateway_service.py tests/hermes_cli/test_gateway_wsl.py tests/hermes_cli/test_ignore_user_config_flags.py tests/hermes_cli/test_service_manager.py tests/hermes_cli/test_signal_handler_kanban_worker.py tests/test_live_system_guard_self_test.py tests/tools/test_base_environment.py tests/tools/test_file_tools.py tests/test_tui_gateway_server.py tests/project_work/test_bindings.py -q` -- passed: 31 files, 1,418 tests.
- `bash scripts/run_tests.sh` -- passed: 1,887 files, 39,307 tests, 0 failed.

## Conclusion

**Confidence:** High

Story 2.1a's focused implementation surface remains valid, the unrelated full-regression blockers have been addressed, and the required completion gate now passes. The correct next step is code review, not further investigation.
