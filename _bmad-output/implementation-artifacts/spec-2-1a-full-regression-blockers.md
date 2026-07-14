---
title: 'Fix Story 2.1a Full Regression Blockers'
type: 'bugfix'
created: '2026-07-14'
status: 'done'
baseline_commit: '69377f4135c68c84ffac96bf6c7f3f159f7517e6'
context:
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/investigations/story-2-1a-full-regression-gate-investigation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 2.1a's focused implementation tests pass, but the dev-story completion gate is blocked because full-regression validation exposed unrelated repo test failures on this Darwin worktree. Several blockers have already been reduced, but the remaining gate still fails on the kanban SIGTERM synthetic liveness test and the TUI browser launch hint test.

**Approach:** Finish the regression cleanup by making the affected tests and production helpers accurately model cross-platform behavior, without weakening the product contracts those tests guard. Preserve existing Story 2.1a implementation behavior and only touch unrelated suites where the failure is already reproduced.

## Boundaries & Constraints

**Always:** Keep Story 2.1a scope unchanged: `hermes_project_work/bindings.py` remains schema/create/read/uniqueness only. Use behavior-contract fixes over brittle snapshots. Preserve real safety semantics: kanban workers with `HERMES_KANBAN_TASK` must terminate promptly after SIGTERM, browser connection errors must still give users actionable launch guidance, and service/file/path tests must pass on Darwin without hiding Linux behavior.

**Ask First:** Halt before changing full-suite policy, skipping a whole test file, relaxing a user-facing safety guard, or broadening Story 2.1a beyond Project Binding persistence.

**Never:** Do not mark Story 2.1a review/done until validation evidence supports it. Do not hardcode this runner's absolute paths. Do not remove tests just to make the suite green. Do not add new core tools or new user-facing env vars.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Kanban worker SIGTERM on Darwin | Synthetic worker exits through `os._exit(0)` and becomes a zombie until the parent reaps it | Test liveness helper treats the exited/zombie child as dead, matching dispatcher semantics | If process is genuinely running, test still fails within bounded timeout |
| Browser connect no executable | `/browser connect` to local CDP port, no browser listening, launch attempt returns false, candidates empty | Response includes unreachable CDP message, explicit no-executable hint, manual `--remote-debugging-port` guidance, and progress events match messages | Do not set `BROWSER_CDP_URL` when connection fails |
| Optional dependency test suites | ACP/WeCom tests run in this local venv | Pinned extras needed by those tests are installed locally or tests remain dependency-aware | Missing optional deps must surface clearly, not as unrelated story failures |
| Darwin path canonicalization | Tests create files under `/tmp`, host resolves to `/private/tmp` | Assertions compare canonical paths where production code intentionally resolves paths | Path checks still verify media/file operation routing by type |

</frozen-after-approval>

## Code Map

- `tests/hermes_cli/test_signal_handler_kanban_worker.py` -- Synthetic regression test for kanban worker SIGTERM behavior; liveness helper currently mirrors Linux zombie detection only.
- `hermes_cli/kanban_db.py` -- Production dispatcher `_pid_alive` already documents Linux and Darwin zombie handling; use as the source of truth for test behavior.
- `tests/test_tui_gateway_server.py` -- Browser JSON-RPC coverage; failing assertion expects a no-executable hint that the response no longer includes.
- `tui_gateway/server.py` -- `browser.manage` handler and `_failure_messages()` response construction for failed CDP connect attempts.
- `hermes_cli/browser_connect.py` -- Browser launch diagnostics and candidate discovery; current logs confirm no Chromium binary on Darwin.
- `agent/anthropic_adapter.py` -- Already patched to treat non-string keychain payloads like invalid JSON.
- `gateway/shutdown_forensics.py` -- Already patched to launch diagnostics on POSIX hosts without GNU `timeout`.
- `hermes_cli/service_manager.py` and related tests -- Already adjusted for mode/platform assumptions and mocked systemd availability.
- `tests/gateway/test_background_command.py`, `tests/tools/test_file_tools.py`, `tests/hermes_cli/test_gateway_wsl.py`, `tests/test_live_system_guard_self_test.py`, `tests/agent/test_anthropic_output_field_leak.py` -- Existing partial fixes that must remain green.

## Tasks & Acceptance

**Execution:**
- [x] `tests/hermes_cli/test_signal_handler_kanban_worker.py` -- Updated `_is_alive_like_dispatcher()` to mirror Darwin zombie detection from production -- fixes the SIGTERM test without weakening the real process-exit contract.
- [x] `tests/test_tui_gateway_server.py`, `tui_gateway/server.py`, and `hermes_cli/browser_connect.py` -- Aligned browser failure messages so no-browser/no-candidate and spawn-failed cases expose actionable guidance consistently -- restores the user-facing diagnostic contract.
- [x] `.venv` dependency state -- Kept local pinned ACP and WeCom extras available for validation (`agent-client-protocol==0.9.0`, `defusedxml==0.7.1`) -- prevents optional-suite collection failures from masking story validation.
- [x] Regression-fix files already touched -- Re-ran focused tests for all formerly failing clusters and kept their fixes intact -- ensures the cleanup did not reintroduce previous failures.
- [x] `_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md` and investigation case file -- Updated Dev Agent Record/investigation evidence sections after final validation -- keeps BMad status honest.

**Acceptance Criteria:**
- Given the current Darwin worktree, when `bash scripts/run_tests.sh tests/hermes_cli/test_signal_handler_kanban_worker.py tests/test_tui_gateway_server.py -q` runs, then both files pass.
- Given all known full-regression blocker files from the investigation, when the targeted blocker suite runs, then it reports zero failed files and zero collection errors.
- Given Story 2.1a focused validation, when `bash scripts/run_tests.sh tests/project_work/test_bindings.py -q` and ruff run, then both still pass.
- Given the full repository regression command is run, when it completes, then any remaining failures are recorded with exact failing files and are not attributed to Story 2.1a without evidence.

## Spec Change Log

## Design Notes

The safest fix style is to align tests with existing production contracts rather than weakening the contracts. For process liveness, `hermes_cli/kanban_db.py:_pid_alive` is the behavior reference because the test claims to mirror dispatcher semantics. For browser diagnostics, user-facing response messages should remain explicit enough that a TUI user knows whether to install Chrome/Chromium or manually start a browser with the expected CDP port.

## Verification

**Commands:**
- `bash scripts/run_tests.sh tests/project_work/test_bindings.py -q` -- passed: 132/132 tests.
- `.venv/bin/python -m ruff check agent/anthropic_adapter.py gateway/shutdown_forensics.py hermes_cli/browser_connect.py hermes_cli/service_manager.py hermes_project_work/bindings.py tools/environments/base.py tests/agent/test_anthropic_keychain.py tests/agent/test_anthropic_output_field_leak.py tests/cli/test_cli_browser_connect.py tests/gateway/test_background_command.py tests/gateway/test_shutdown_forensics.py tests/hermes_cli/test_gateway_service.py tests/hermes_cli/test_gateway_wsl.py tests/hermes_cli/test_ignore_user_config_flags.py tests/hermes_cli/test_service_manager.py tests/hermes_cli/test_signal_handler_kanban_worker.py tests/project_work/test_bindings.py tests/test_live_system_guard_self_test.py tests/test_tui_gateway_server.py tests/tools/test_base_environment.py tests/tools/test_file_tools.py tui_gateway/server.py` -- passed.
- `bash scripts/run_tests.sh tests/agent/test_anthropic_keychain.py tests/gateway/test_shutdown_forensics.py tests/cli/test_cli_browser_connect.py tests/test_tui_gateway_server.py tests/tools/test_base_environment.py -q` -- passed: 5 files, 406 tests.
- `bash scripts/run_tests.sh tests/agent/test_anthropic_adapter.py tests/agent/test_anthropic_keychain.py tests/agent/test_anthropic_output_field_leak.py tests/acp tests/cli/test_cli_browser_connect.py tests/gateway/test_background_command.py tests/gateway/test_shutdown_forensics.py tests/gateway/test_wecom_callback.py tests/hermes_cli/test_gateway_service.py tests/hermes_cli/test_gateway_wsl.py tests/hermes_cli/test_ignore_user_config_flags.py tests/hermes_cli/test_service_manager.py tests/hermes_cli/test_signal_handler_kanban_worker.py tests/test_live_system_guard_self_test.py tests/tools/test_base_environment.py tests/tools/test_file_tools.py tests/test_tui_gateway_server.py tests/project_work/test_bindings.py -q` -- passed: 31 files, 1,418 tests.
- `bash scripts/run_tests.sh` -- passed: 1,887 files, 39,307 tests, 0 failed.

## Suggested Review Order

**Project Binding Persistence**

- Schema contract verifies columns, primary key, indexes, and predicates.
  [`bindings.py:306`](../../hermes_project_work/bindings.py#L306)

- Additive repair restores schema metadata without deleting persisted rows.
  [`bindings.py:369`](../../hermes_project_work/bindings.py#L369)

- Validation rejects ambiguous paths, controller identity, and bad JSON.
  [`bindings.py:560`](../../hermes_project_work/bindings.py#L560)

- Acceptance tests prove persistence, conflicts, repair, and races.
  [`test_bindings.py:151`](../../tests/project_work/test_bindings.py#L151)

**Regression Blockers**

- Snapshot temp files use `mktemp` to avoid Darwin bash collisions.
  [`base.py:387`](../../tools/environments/base.py#L387)

- Shutdown diagnostics stay bounded without GNU `timeout`.
  [`shutdown_forensics.py:243`](../../gateway/shutdown_forensics.py#L243)

- Browser failures distinguish missing executables from failed launches.
  [`server.py:13172`](../../tui_gateway/server.py#L13172)

- Spawn failures now surface concrete browser launch guidance.
  [`browser_connect.py:257`](../../hermes_cli/browser_connect.py#L257)

- Keychain reader treats non-object JSON as absent credentials.
  [`anthropic_adapter.py:909`](../../agent/anthropic_adapter.py#L909)

**Platform Test Alignment**

- Darwin worker liveness mirrors production zombie detection.
  [`test_signal_handler_kanban_worker.py:81`](../../tests/hermes_cli/test_signal_handler_kanban_worker.py#L81)

- File-tool expectations compare canonical resolved paths.
  [`test_file_tools.py:17`](../../tests/tools/test_file_tools.py#L17)

- Systemd service tests model availability instead of host assumptions.
  [`test_gateway_service.py:21`](../../tests/hermes_cli/test_gateway_service.py#L21)

- Live systemctl pass-through tests skip when systemctl is absent.
  [`test_live_system_guard_self_test.py:32`](../../tests/test_live_system_guard_self_test.py#L32)
