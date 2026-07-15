---
stepsCompleted:
  - 'step-01-preflight-and-context'
  - 'step-02-generation-mode'
  - 'step-03-test-strategy'
  - 'step-04-generate-tests'
  - 'step-05-validate-and-complete'
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-07-16'
storyId: '2.1b'
storyKey: '2-1b-validate-project-binding-safety-and-conflicts'
storyFile: '_bmad-output/implementation-artifacts/2-1b-validate-project-binding-safety-and-conflicts.md'
atddChecklistPath: '_bmad-output/test-artifacts/atdd-checklist-2-1b-validate-project-binding-safety-and-conflicts.md'
generatedTestFiles:
  - 'tests/project_work/test_bindings.py'
inputDocuments:
  - '_bmad-output/implementation-artifacts/2-1b-validate-project-binding-safety-and-conflicts.md'
  - '_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md'
  - '_bmad-output/test-artifacts/test-design-epic-2.1b.md'
  - '_bmad-output/project-context.md'
  - 'hermes_project_work/bindings.py'
  - 'tests/project_work/test_bindings.py'
  - 'hermes_constants.py'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/operational-diagnostic.schema.json'
---

# ATDD Checklist: Story 2.1b — Validate Project Binding Safety And Conflicts

**Mode:** Create (sequential, AI generation) · **Detected stack:** `backend` (Python-only story; repo overall is fullstack but this story adds no frontend/API/HTTP surface) · **Generation mode:** AI generation, no recording (backend → no browser surface) · **Test levels used:** Unit (private validation helpers) + Integration (real SQLite, real `tmp_path` filesystem) + Contract vocabulary + Regression/static guards. No E2E/Playwright (W-01/W-05: no public command/API/tool surface exists yet for this story).

## Prerequisites Verified

- Story `2-1b-validate-project-binding-safety-and-conflicts.md` is `ready-for-dev` with 7 clear acceptance criteria. ✅
- Test Design artifact `_bmad-output/test-artifacts/test-design-epic-2.1b.md` is `completed` (all 5 steps), with 20 P0 + 30 P1 conceptual scenarios, 11 waivers (W-01–W-11), and full AC/risk/reviewer-concern traceability tables. ✅
- Test framework: `pytest==9.0.2` via `scripts/run_tests.sh`; `pyproject.toml` `[tool.pytest.ini_options]` present. ✅
- Target module `hermes_project_work/bindings.py` **already exists and imports cleanly** (Story 2.1a shipped it). Only this story's new symbols (`_check_cwd_safety`, `_check_bmad_reference_safety`, `_check_github_reference_safety`, `_check_provider_metadata_safety`, `_CONFLICT_CATEGORY_BY_DIMENSION`, `preview_binding_conflicts()`, `validate_binding()`, and the `exclude_binding_id` kwarg on `_check_uniqueness_dimensions()`) are missing — confirmed via `grep`/`Read` during preflight. This is why every new scaffold below is an **executable red test** (fails with `AttributeError`/`TypeError` today), not a skip-gated scaffold — the module boundary already exists, only specific attributes are missing.
- Existing pattern to extend confirmed: `tests/project_work/test_bindings.py` (Story 2.1a's suite) already uses the `conn`/`db_path` fixtures and `row_count()`/`get_row()` helpers this story's tests build on. Per the story's own Dev Notes ("Project Structure Notes"), all new tests were added to this same file — no new test file was created.
- Ran the full file after adding the new section: `scripts/run_tests.sh tests/project_work/test_bindings.py -q` → **67 failed, 138 passed**. All 67 failures are the expected `AttributeError`/`TypeError` for the not-yet-implemented Tasks 1–5 symbols (verified by grepping the failure messages — no incidental test bugs). The 138 passing tests are Story 2.1a's untouched suite plus this story's `TestScopeRegressionGuards` and diagnostic-vocabulary static checks, which are designed to pass both before and after implementation.
- `ruff check tests/project_work/test_bindings.py` → all checks passed.

## Red-Phase Disposition Summary

Unlike Story 2.1a's ATDD scaffold (where the whole module was skip-gated because it didn't exist), this story's scaffold is **executable-red by default**: the story pins exact function names and signatures in Tasks 1–5, so there is no "assumed contract" ambiguity to hide behind a skip. Every P0/P1 TD scenario and every reviewer concern is one of:

- **Executable red test** — calls the not-yet-implemented symbol directly; fails today with `AttributeError` (or, for the `exclude_binding_id` kwarg, `TypeError`); will pass once the corresponding Task lands. This is the disposition for the large majority of scenarios.
- **Executable regression/static guard** — passes today and must keep passing after implementation (scope-creep guards, schema-column guards, existing 2.1a suite). Not "red," by design.
- **Waiver** — already defined in the TD artifact (W-01 through W-11); carried forward unchanged, no new waivers were needed.

## Acceptance Criteria → Tests

| AC | Generated tests (all in `tests/project_work/test_bindings.py`) | Disposition |
| --- | --- | --- |
| AC1 (invalid/outside-root cwd rejects with diagnostic) | `TestCwdSafetyValidation::test_missing_cwd_reports_does_not_exist`, `::test_filesystem_root_reports_is_filesystem_root`, `::test_exact_hermes_home_reports_within_hermes_home`, `::test_nested_hermes_home_reports_within_hermes_home`, `::test_existence_check_gates_hermes_home_check`; `TestValidateBinding::test_cwd_that_never_existed_returns_invalid_cwd_diagnostic`, `::test_validation_state_precedence_cwd_wins_over_everything`, `::test_stale_cwd_deleted_after_create_becomes_unsafe`; `TestDiagnosticContractVocabulary::test_invalid_cwd_diagnostic_uses_repair_project_binding` | Executable red (actual action-block deferred to Story 2.3 — W-01/W-05) |
| AC2 (cross-binding conflicts block automation with refs + category) | `TestPreviewBindingConflicts::test_cwd_conflict_*` / `test_github_conflict_*` / `test_bmad_conflict_*` / `test_provider_conflict_*` / `test_all_four_dimensions_conflict_*`; `TestValidateBinding::test_never_reports_self_as_conflict`, `::test_exclude_binding_id_only_excludes_the_specified_row`, `::test_validate_binding_conflict_diagnostic_uses_update_project_binding`; `TestDiagnosticContractVocabulary::test_conflict_categories_map_exact_dimension_strings` | Executable red (non-empty `validate_binding().conflicts` only forced via monkeypatched seam per W-11 — see note below) |
| AC3 (cwd exists but not a git repo is unsafe) | `TestCwdSafetyValidation::test_directory_without_git_reports_not_a_git_repository`, `::test_directory_with_git_is_valid`, `::test_directory_check_gates_git_check`, `::test_hermes_home_check_gates_git_check`; `TestValidateBinding::test_existing_non_git_cwd_flagged_not_a_git_repository`, `::test_stale_git_removed_after_create_becomes_unsafe` | Executable red |
| AC4 (missing BMAD dir reports invalid diagnostic, no exception) | `TestBmadReferenceSafety::*` (all 4); `TestValidateBinding::test_missing_bmad_dir_returns_invalid_bmad_reference_diagnostic`, `::test_existing_bmad_dir_remains_safe`, `::test_stale_bmad_dir_deleted_after_create_becomes_unsafe`; `TestDiagnosticContractVocabulary::test_invalid_bmad_reference_diagnostic_uses_repair_project_binding` | Executable red |
| AC5 (malformed GitHub/provider metadata returns diagnostic, not exception) | `TestGithubAndProviderMetadataSafety::*` (all 9); `TestValidateBinding::test_malformed_github_reference_json_*`, `::test_github_reference_non_dict_json_*`, `::test_malformed_provider_metadata_json_*`, `::test_provider_metadata_non_dict_json_*`, `::test_one_sided_provider_identity_raw_row_*`, `::test_provider_metadata_without_identity_raw_row_*`, `::test_one_malformed_field_does_not_prevent_other_checks`; `TestDiagnosticContractVocabulary::test_invalid_github_reference_diagnostic_*` / `test_invalid_provider_metadata_diagnostic_*` | Executable red |
| AC6 (fully valid, non-conflicting binding → valid/safe/no diagnostics/no conflicts) | `TestValidateBinding::test_fully_valid_binding_is_safe_with_no_diagnostics_or_conflicts`, `::test_existing_bmad_dir_remains_safe`, `::test_safe_iff_all_checks_valid_and_conflicts_empty`, `::test_never_reports_self_as_conflict`; `TestCwdSafetyValidation::test_directory_with_git_is_valid` | Executable red |
| AC7 (candidate preview returns conflicting dimension + existing id, no row created) | `TestPreviewBindingConflicts::*` (all 11) | Executable red |

## Mandatory Traceability — TD Scenario → Test

| TD ID | Priority | Test | Disposition |
| --- | --- | --- | --- |
| 2.1B-UNIT-001 | P0 | `TestCwdSafetyValidation::test_missing_cwd_reports_does_not_exist` | Executable red |
| 2.1B-UNIT-002 | P0 | `TestCwdSafetyValidation::test_file_not_directory_reports_not_a_directory` | Executable red |
| 2.1B-UNIT-003 | P0 | `TestCwdSafetyValidation::test_filesystem_root_reports_is_filesystem_root` | Executable red |
| 2.1B-UNIT-004 | P0 | `TestCwdSafetyValidation::test_exact_hermes_home_reports_within_hermes_home`, `::test_nested_hermes_home_reports_within_hermes_home` | Executable red |
| 2.1B-UNIT-005 | P0 | `TestCwdSafetyValidation::test_directory_without_git_reports_not_a_git_repository` | Executable red |
| 2.1B-INT-001 | P0 | `TestValidateBinding::test_cwd_that_never_existed_returns_invalid_cwd_diagnostic` | Executable red |
| 2.1B-INT-002 | P0 | `TestValidateBinding::test_existing_non_git_cwd_flagged_not_a_git_repository` | Executable red |
| 2.1B-INT-003 | P0 | `TestValidateBinding::test_fully_valid_binding_is_safe_with_no_diagnostics_or_conflicts` | Executable red |
| 2.1B-INT-004 | P0 | `TestValidateBinding::test_malformed_github_reference_json_returns_diagnostic_no_exception` | Executable red |
| 2.1B-INT-005 | P0 | `TestValidateBinding::test_github_reference_non_dict_json_returns_diagnostic_no_exception` | Executable red |
| 2.1B-INT-006 | P0 | `TestValidateBinding::test_malformed_provider_metadata_json_returns_diagnostic_no_exception` | Executable red |
| 2.1B-INT-007 | P0 | `TestValidateBinding::test_provider_metadata_non_dict_json_returns_diagnostic_no_exception`, `::test_one_sided_provider_identity_raw_row_returns_diagnostic_no_exception`, `::test_provider_metadata_without_identity_raw_row_returns_diagnostic` | Executable red |
| 2.1B-INT-008 | P0 | `TestPreviewBindingConflicts::test_cwd_conflict_returns_category_and_existing_id` | Executable red |
| 2.1B-INT-009 | P0 | `TestPreviewBindingConflicts::test_github_conflict_returns_category_and_existing_id` | Executable red |
| 2.1B-INT-010 | P0 | `TestPreviewBindingConflicts::test_bmad_conflict_returns_category_and_existing_id` | Executable red |
| 2.1B-INT-011 | P0 | `TestPreviewBindingConflicts::test_provider_conflict_returns_category_and_existing_id` | Executable red |
| 2.1B-INT-012 | P0 | `TestPreviewBindingConflicts::test_all_four_dimensions_conflict_reports_all_categories` | Executable red |
| 2.1B-INT-013 | P0 | `TestValidateBinding::test_validation_state_precedence_cwd_wins_over_everything`, `::test_validation_state_precedence_bmad_before_github_and_provider`, `::test_validation_state_precedence_github_before_provider` | Executable red |
| 2.1B-INT-014 | P0 | `TestValidateBinding::test_safe_iff_all_checks_valid_and_conflicts_empty` | Executable red |
| 2.1B-CONTRACT-001 | P0 | `TestDiagnosticContractVocabulary::*` (5 tests); `TestValidateBinding::test_validate_binding_conflict_diagnostic_uses_update_project_binding` (conflict-recovery-option branch, monkeypatched — see note below) | Executable red |
| 2.1B-UNIT-006 | P1 | `TestCwdSafetyValidation::test_directory_with_git_is_valid` | Executable red |
| 2.1B-UNIT-007 | P1 | `TestBmadReferenceSafety::test_none_input_returns_none` | Executable red |
| 2.1B-UNIT-008 | P1 | `TestBmadReferenceSafety::test_missing_directory_reports_invalid` | Executable red |
| 2.1B-UNIT-009 | P1 | `TestBmadReferenceSafety::test_file_not_directory_reports_invalid` | Executable red |
| 2.1B-UNIT-010 | P1 | `TestBmadReferenceSafety::test_existing_directory_returns_valid` | Executable red |
| 2.1B-UNIT-011 | P1 | `TestGithubAndProviderMetadataSafety::test_github_reference_none_returns_valid`, `::test_github_reference_valid_dict_returns_valid` | Executable red |
| 2.1B-UNIT-012 | P1 | `TestGithubAndProviderMetadataSafety::test_github_reference_converts_raised_errors_to_invalid[*]` (3 cases) | Executable red |
| 2.1B-UNIT-013 | P1 | `TestGithubAndProviderMetadataSafety::test_provider_metadata_safety_absent_identity_returns_valid`, `::test_provider_metadata_safety_complete_identity_returns_valid` | Executable red |
| 2.1B-UNIT-014 | P1 | `TestGithubAndProviderMetadataSafety::test_provider_metadata_safety_converts_raised_errors_to_invalid[*]` (3 cases), `::test_provider_metadata_safety_non_dict_metadata_returns_invalid` | Executable red |
| 2.1B-INT-015 | P1 | `TestValidateBinding::test_never_reports_self_as_conflict` | Executable red |
| 2.1B-INT-016 | P1 | `TestValidateBinding::test_exclude_binding_id_only_excludes_the_specified_row` | Executable red |
| 2.1B-INT-017 | P1 | `TestValidateBinding::test_unknown_binding_id_raises_value_error` | Executable red |
| 2.1B-INT-018 | P1 | `TestValidateBinding::test_missing_bmad_dir_returns_invalid_bmad_reference_diagnostic` | Executable red |
| 2.1B-INT-019 | P1 | `TestValidateBinding::test_existing_bmad_dir_remains_safe` | Executable red |
| 2.1B-INT-020 | P1 | `TestValidateBinding::test_one_malformed_field_does_not_prevent_other_checks` | Executable red |
| 2.1B-INT-021 | P1 | `TestPreviewBindingConflicts::test_non_conflicting_candidate_returns_empty_list` | Executable red |
| 2.1B-INT-022 | P1 | `TestPreviewBindingConflicts::test_preview_normalizes_candidate_like_create_binding` | Executable red |
| 2.1B-INT-023 | P1 | `TestPreviewBindingConflicts::test_invalid_provider_candidate_raises_before_sql` | Executable red |
| 2.1B-INT-024 | P1 | `TestPreviewBindingConflicts::test_profile_none_resolves_active_profile` | Executable red |
| 2.1B-INT-025 | P1 | `TestPreviewBindingConflicts::test_same_values_different_profile_no_conflict` | Executable red |
| 2.1B-INT-026 | P1 | `TestPreviewBindingConflicts::test_repeated_preview_is_idempotent_and_creates_no_row` | Executable red |
| 2.1B-INT-027 | P1 | `TestValidateBinding::test_stale_cwd_deleted_after_create_becomes_unsafe` | Executable red |
| 2.1B-INT-028 | P1 | `TestValidateBinding::test_stale_git_removed_after_create_becomes_unsafe` | Executable red |
| 2.1B-INT-029 | P1 | `TestValidateBinding::test_stale_bmad_dir_deleted_after_create_becomes_unsafe` | Executable red |
| 2.1B-INT-030 | P1 | `TestValidateBinding::test_one_sided_provider_identity_raw_row_returns_diagnostic_no_exception`, `::test_provider_metadata_without_identity_raw_row_returns_diagnostic` | Executable red |
| 2.1B-INT-031 | P1 | `TestValidateBinding::test_diagnostic_messages_are_nonempty_actionable_and_tagged` | Executable red |
| 2.1B-REG-001 | P1 | `TestScopeRegressionGuards::test_no_new_lifecycle_or_audit_columns_added`, `::test_migration_seam_unchanged_no_new_column_ddl` | **Executable now (regression guard, passes today)** |
| 2.1B-REG-002 | P1 | Covered by the unmodified, still-passing Story 2.1a suite above this section (`TestP0BlockingCases`, `TestRequiredFieldValidationP1`, etc.) — no new test needed; verified green in the same `-q` run (138 passed). | Satisfied by existing suite |
| 2.1B-REG-003 | P1 | `TestScopeRegressionGuards::test_no_activation_or_lifecycle_functions_added`, `::test_no_cli_or_toolset_wiring_references_new_validation_functions` | **Executable now (regression guard, passes today)** |
| 2.1B-REG-004 | P1 | Satisfied structurally: every new test in this section lives in `tests/project_work/test_bindings.py` (no new file) and uses the `conn`/`tmp_path` real-SQLite/real-filesystem fixtures already established by Story 2.1a. | Satisfied by construction |

## Reviewer Concerns → Tests

| Reviewer concern | Test(s) | Disposition |
| --- | --- | --- |
| No activation command in this story | `TestScopeRegressionGuards::test_no_activation_or_lifecycle_functions_added` | Regression guard (W-01, W-05) |
| No durable lifecycle columns/status/audit | `TestScopeRegressionGuards::test_no_new_lifecycle_or_audit_columns_added` | Regression guard (W-02) |
| No BMAD mount mutation / provider liveness | `TestScopeRegressionGuards::test_no_activation_or_lifecycle_functions_added` (name-based guard); no dedicated runtime test — mount/liveness subsystems are untouched by this story's design | Waiver carried forward (W-03, W-04) |
| Cwd safety failure order (existence → directory → root → Hermes home → git) | `TestCwdSafetyValidation::test_existence_check_gates_hermes_home_check`, `::test_directory_check_gates_git_check`, `::test_hermes_home_check_gates_git_check` | Executable red |
| Root/Hermes-home denylist | `TestCwdSafetyValidation::test_filesystem_root_reports_is_filesystem_root`, `::test_exact_hermes_home_reports_within_hermes_home`, `::test_nested_hermes_home_reports_within_hermes_home` | Executable red |
| `.git` directory convention (no `git rev-parse`) | `TestCwdSafetyValidation::test_directory_without_git_reports_not_a_git_repository`; static review at implementation time confirms no subprocess/`git` dependency added | Executable red + code-review note |
| Wrap, don't reimplement, GitHub/provider validators | `TestGithubAndProviderMetadataSafety::test_github_reference_safety_wraps_not_reimplements_validator`, `::test_provider_metadata_safety_wraps_not_reimplements_validator` | Executable red |
| Raw-row validation avoids `_binding_from_row()` exception | `TestValidateBinding::test_malformed_github_reference_json_*`, `::test_malformed_provider_metadata_json_*`, `::test_github_reference_non_dict_json_*`, `::test_provider_metadata_non_dict_json_*` | Executable red |
| Malformed field invalidates only that check, continues | `TestValidateBinding::test_one_malformed_field_does_not_prevent_other_checks` | Executable red |
| Preview is read-only | Every `TestPreviewBindingConflicts` test asserts `row_count(conn) == before` | Executable red |
| Exact conflict categories | `TestDiagnosticContractVocabulary::test_conflict_categories_map_exact_dimension_strings` | Executable red |
| SQL self-exclusion, not post-filter-only | `TestValidateBinding::test_exclude_binding_id_only_excludes_the_specified_row` | Executable red |
| Do not force two persisted colliding rows | No test attempts this (by design, per the story's own Task 4 guidance); `test_never_reports_self_as_conflict` documents the invariant instead, and `test_validate_binding_conflict_diagnostic_uses_update_project_binding` exercises the diagnostic-assembly branch via a monkeypatched seam rather than real rows | Waiver carried forward (W-11) |
| Exact diagnostic owner/recovery strings | `TestDiagnosticContractVocabulary::*`; `TestValidateBinding::test_validate_binding_conflict_diagnostic_uses_update_project_binding` | Executable red |
| Local diagnostic categories ≠ schema coarse categories | Implicit in all category assertions (`invalid_cwd`, `cwd_conflict`, etc.) never compared against the schema's `category` enum | Executable red + W-06 for durable schema |
| Validation-state precedence | `TestValidateBinding::test_validation_state_precedence_*` (3 tests) | Executable red |
| Safe iff valid | `TestValidateBinding::test_safe_iff_all_checks_valid_and_conflicts_empty` | Executable red |
| Unknown id raises `ValueError` | `TestValidateBinding::test_unknown_binding_id_raises_value_error` | Executable red |
| Create path remains fail-fast | Existing Story 2.1a suite, unmodified and still green | Satisfied by existing suite |
| Tests colocated, real SQLite/tmp path | Structural — see 2.1B-REG-004 | Satisfied by construction |
| No CLI/tool/core wiring or new infra | `TestScopeRegressionGuards::test_no_cli_or_toolset_wiring_references_new_validation_functions` | Regression guard (W-01) |
| Durable operational diagnostics deferred | No persistence test added (correctly out of scope) | Waiver carried forward (W-06) |
| Provider metadata one-sided identity handling | `TestValidateBinding::test_one_sided_provider_identity_raw_row_returns_diagnostic_no_exception`, `TestGithubAndProviderMetadataSafety::test_provider_metadata_safety_converts_raised_errors_to_invalid[*]` | Executable red |

## Waivers Carried Forward From Test Design (unchanged — no new waivers needed)

| Waiver | Reason | Owner | Residual risk | Follow-up trigger |
| --- | --- | --- | --- | --- |
| W-01 Actual activation command / public authorization | This story ships `validate_binding()`/`preview_binding_conflicts()` only; no `activate_binding()`. | Owner of Story 2.1c/2.3 or first public caller | A future caller could start workflow actions without checking validation first. | Any command/API/tool/gateway/workflow action calls Project Binding validation. |
| W-02 Durable lifecycle state | `enabled`, persisted `validation_state`, update/disable/repair/re-enable, audit history belong to Story 2.1c. | Story 2.1c owner | Validation is recomputed correctly but not persisted/audited until 2.1c. | Any durable lifecycle column/command is added. |
| W-03 BMAD mount mutation | Mounting, reload, wrong-project mount diagnostics belong to Story 2.2. | Story 2.2 owner | A valid `bmad_skill_dir` path is not proof BMAD skills are mounted/usable. | Any code mutates skill directories or invokes BMAD through the stored reference. |
| W-04 Provider lifecycle / liveness | Archon registration/status/stale/rotated states belong to Story 3.2+. | Story 3.2/provider-integration owner | Stored provider metadata can be structurally valid but operationally stale. | Any provider adapter inspects/registers/refreshes provider binding health. |
| W-05 Workflow action cwd enforcement | Actually gating workflow action start on validation belongs to Story 2.3. | Story 2.3 owner | Validation can report unsafe while a future action path forgets to call it. | Any workflow execution path is introduced. |
| W-06 Durable OperationalDiagnostic persistence | Plain diagnostic dicts here; stable IDs/severity/redaction/persistence belong to Story 5.3a. | Story 5.3a owner | Plain diagnostics may not yet satisfy the full schema. | Any diagnostic history/persistence/query feature is added. |
| W-07 External Archon producer evidence | Validates local stored shape/vocabulary only; no live Archon consumption. | Provider-integration owner | Local fixtures don't prove real Archon compatibility. | Before any provider-dependent consumer story is marked done. |
| W-08 Async events, out-of-order delivery, timeout, cancellation | APIs are synchronous local functions; no queue/timeout/cancellation exists. | First async/event-driven binding operation owner | Later orchestration could mishandle stale events/duplicates/timeouts. | Add event ingestion, background validation, retries, timeouts, or cancellation. |
| W-09 Performance/scalability SLO | No product threshold exists for binding count/validation latency. | Product owner + operations | Large stores could regress without a measurable gate. | An SLO/scale envelope/benchmark requirement is approved. |
| W-10 Physical path alias equivalence | Physical identity via symlink/case-folding is not specified; tests deliberately avoid depending on symlink-resolution edge cases. | Architect + platform owner | The same repository may be reachable through aliases on some platforms. | Architecture chooses `realpath`/case-folding semantics, or CI exposes alias-collision misses. |
| W-11 Non-empty existing-binding conflict list | Hard unique indexes make two persisted colliding rows in one profile impossible through supported writes; the reachable path is `preview_binding_conflicts()`, not `validate_binding()`'s re-scan. | Story 2.1c update-path owner | A future update path or damaged DB could need the existing-binding conflict scan. | Any update path bypasses create-time uniqueness checks, or schema/index repair behavior changes. |

## Commands To Run

```bash
# Full focused suite for this story (and 2.1a's untouched suite in the same file)
scripts/run_tests.sh tests/project_work/test_bindings.py -q

# Lint check (project convention)
ruff check tests/project_work/test_bindings.py

# Just this story's new red-phase classes, once Tasks 1-5 land
scripts/run_tests.sh tests/project_work/test_bindings.py -q -k \
  "TestCwdSafetyValidation or TestBmadReferenceSafety or TestGithubAndProviderMetadataSafety or \
   TestPreviewBindingConflicts or TestValidateBinding or TestDiagnosticContractVocabulary"

# Regression/static guards only (should always be green, before and after implementation)
scripts/run_tests.sh tests/project_work/test_bindings.py -q -k TestScopeRegressionGuards
```

## Current Observed State (baseline, captured during this ATDD run)

`scripts/run_tests.sh tests/project_work/test_bindings.py -q` → **67 failed, 138 passed**.

All 67 failures are `AttributeError: module 'hermes_project_work.bindings' has no attribute '<name>'` for `validate_binding` (26), `preview_binding_conflicts` (11), `_check_cwd_safety` (10), `_check_provider_metadata_safety` (7), `_check_github_reference_safety` (6), `_check_bmad_reference_safety` (4), plus one `TypeError: _check_uniqueness_dimensions() got an unexpected keyword argument 'exclude_binding_id'` — exactly the seven symbols/signature-extension Tasks 1–5 must add. No incidental test bugs were present in this baseline run.
