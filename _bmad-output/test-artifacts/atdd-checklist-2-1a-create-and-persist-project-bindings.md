---
stepsCompleted:
  - 'step-01-preflight-and-context'
  - 'step-02-generation-mode'
  - 'step-03-test-strategy'
  - 'step-04-generate-tests'
  - 'step-05-validate-and-complete'
lastStep: 'step-05-validate-and-complete'
lastSaved: '2026-07-13'
storyId: '2.1a'
storyKey: '2-1a-create-and-persist-project-bindings'
storyFile: '_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md'
atddChecklistPath: '_bmad-output/test-artifacts/atdd-checklist-2-1a-create-and-persist-project-bindings.md'
generatedTestFiles:
  - 'tests/project_work/__init__.py'
  - 'tests/project_work/test_bindings.py'
inputDocuments:
  - '_bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md'
  - '_bmad-output/test-artifacts/test-design-epic-2.1a.md'
  - '_bmad-output/project-context.md'
  - 'hermes_cli/projects_db.py'
  - 'hermes_cli/sqlite_util.py'
  - 'hermes_state.py'
  - 'hermes_constants.py'
  - 'hermes_cli/kanban_db.py'
  - 'hermes_cli/profiles.py'
  - 'tests/hermes_cli/test_projects_db.py'
  - 'tests/conftest.py'
  - 'tests/stress/test_atypical_scenarios.py'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/workflow-provider-binding.schema.json'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/examples/providers/archon/bindings/status-valid.json'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/examples/materialization/new-story.json'
  - '_bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py'
---

# ATDD Checklist: Story 2.1a — Create And Persist Project Bindings

**Mode:** Create (sequential, AI generation) · **Detected stack:** `backend` (Python-only story; repo overall is fullstack but this story adds no frontend/API-HTTP surface) · **Generation mode:** AI generation, no recording (backend → no browser surface) · **Test levels used:** Integration (real SQLite, `tmp_path`) + Unit (exercised through create/read, since the story does not commit to public path/id/key-helper names) + Contract validation. No E2E/Playwright (W-08: no public command/API/tool surface exists yet).

## Prerequisites Verified

- Story `2-1a-create-and-persist-project-bindings.md` is `ready-for-dev` with 4 clear acceptance criteria. ✅
- Test framework: `pytest==9.0.2` via `scripts/run_tests.sh`; `pyproject.toml` `[tool.pytest.ini_options]` present. ✅ (installed dev extras into the project `.venv` via `uv sync --extra dev` to run pytest locally — not a story concern, just an environment note.)
- Existing pattern to clone confirmed: `hermes_cli/projects_db.py` + `hermes_cli/sqlite_util.py` + `tests/hermes_cli/test_projects_db.py` (fixture convention: `pdb.connect(db_path=tmp_path / "...")`). ✅
- Target module `hermes_project_work/bindings.py` and target test package `tests/project_work/` **do not exist yet** — confirmed via filesystem search. This is expected (Story 2.1a Task 1 creates them) and is the reason nearly every generated test is a **skipped red scaffold**, not an executable one.
- Shipped Workflow Commander contract validator (`_bmad-output/planning-artifacts/contracts/workflow-commander/validate_contracts.py`) runs and passes today under the project's Python 3.11 venv (`uv run python3 validate_contracts.py` from its own directory). Confirmed by direct execution during preflight.

## Important caveat carried from the Test Design doc

`_bmad-output/test-artifacts/test-design-epic-2.1a.md` is explicitly marked **Draft — pre-implementation P0 contract decisions open** (R-001 blank-required-field behavior, R-002 uniqueness details, R-003 GitHub reference shape, R-004 provider structural identity). Those product/architecture decisions were **not** re-litigated here; instead this scaffold makes each one an explicit, documented assumption (see the module docstring in `tests/project_work/test_bindings.py`) so the red-phase tests can exist now and drive implementation, rather than blocking ATDD generation entirely:

- **R-001**: blank/`None` required fields (`profile`, `display_name`, `bound_project_cwd`) are assumed to raise `ValueError` before normalization, mirroring `hermes_cli.projects_db.create_project`'s existing `if not name: raise ValueError(...)` precedent.
- **R-002/R-005**: `create_binding()` is assumed to return a dict — `{"conflict": False, "id": "pb_..."}` on success or `{"conflict": True, "violations": {<dimension>: <existing_id>, ...}}` on collision — per the story's own wording in Task 2.
- **R-003**: `github_reference` input is assumed to be `{"owner": str, "repo": str}`, canonicalized as lowercased `"owner/repo"`.
- **R-004**: resolved by the story's own Dev Notes + the real `workflow-provider-binding.schema.json` / `status-valid.json` fixture — not actually blocked; `provider_metadata` stores the `bindingRef` remainder (`bindingId`, `projectRef`) opaquely alongside the two indexed `provider_name`/`provider_binding_name` columns.

**If dev-story lands different exception types or a different result shape, update the assumed-contract section and the affected assertions — the scenarios/behavior being asserted do not change, only the literal call/return shape.**

## Acceptance Criteria → Tests

| AC | Generated tests (all in `tests/project_work/test_bindings.py`) | Status |
| --- | --- | --- |
| AC1 (create + restart identity) | `TestCreateReadRestart::test_fresh_create_persists_normalized_row_with_stable_id` (INT-001), `::test_new_connection_reads_unchanged_id_and_every_field` (INT-002), `TestUniquenessAndNormalization::test_multiple_rows_with_all_optional_refs_null_are_allowed` (INT-009), `TestProviderIdentityAndFixtureRoundtrip::test_real_provider_fixture_roundtrips_after_restart` (INT-016), `TestProfileIsolation::test_db_path_resolves_under_context_local_profile_home` / `::test_active_profile_stores_correctly_resolver_exception_falls_back_default` / `::test_separate_profile_homes_cannot_read_each_others_bindings` (INT-027–029), `TestIdentityStability::test_stored_id_not_recomputed_from_changed_input` (INT-040) | Skipped red scaffolds |
| AC2 (uniqueness, fail-closed, no partial write) | `TestUniquenessAndNormalization::test_equivalent_cwd_spellings_collide` / `::test_equivalent_bmad_dir_spellings_collide` (INT-010/011), `TestP0BlockingCases::test_semantically_equal_github_references_collide` (INT-013, P0), `TestConflictAggregationAndRetryDiscipline::*` (INT-019–024, incl. P0 INT-019), `TestFailureInjectionAndRollback::test_injected_insert_failure_rolls_back_zero_row_and_later_reuse_works` (INT-042) | Skipped red scaffolds |
| AC3 (read returns all persisted fields exactly, incl. after restart) | `TestCreateReadRestart::test_unknown_binding_id_returns_none_without_mutation` / `::test_profile_list_returns_only_that_profile` (INT-003/004), `TestGithubReferenceCanonicalization::test_valid_github_json_preserved_exactly_with_separate_canonical_key` (INT-015), `TestProfileIsolation::test_mixed_profile_explicit_db_list_filters_correctly` (INT-026), `TestJsonUnicodeAndCorruptionHandling::*` (INT-037, INT-039) | Skipped red scaffolds |
| AC4 (idempotent, additive migration/reopen) | `TestMigrationAndIdempotentInit::*` (INT-030–035) | Skipped red scaffolds |

## Mandatory Traceability — TD Scenario → Test

All 49 TD-conceptual scenarios (4 P0, 44 P1, 1 P2) plus the 3 UNIT scenarios are represented below as skipped red scaffolds in `tests/project_work/test_bindings.py`, except VAL-001 which is executable now.

| TD ID | Priority | Test | Disposition |
| --- | --- | --- | --- |
| INT-001 | P1 | `TestCreateReadRestart::test_fresh_create_persists_normalized_row_with_stable_id` | Skipped scaffold |
| INT-002 | P1 | `TestCreateReadRestart::test_new_connection_reads_unchanged_id_and_every_field` | Skipped scaffold |
| INT-003 | P1 | `TestCreateReadRestart::test_unknown_binding_id_returns_none_without_mutation` | Skipped scaffold |
| INT-004 | P1 | `TestCreateReadRestart::test_profile_list_returns_only_that_profile` | Skipped scaffold |
| INT-005 | P1 | `TestRequiredFieldValidationP1::test_reject_blank_profile_zero_mutation` | Skipped scaffold |
| INT-006 | P1 | `TestRequiredFieldValidationP1::test_reject_blank_display_name_zero_mutation` | Skipped scaffold |
| INT-007 | **P0** | `TestP0BlockingCases::test_reject_blank_cwd_before_normalization_zero_mutation` | Skipped scaffold |
| INT-008 | P1 | `TestRequiredFieldValidationP1::test_reject_none_or_unsupported_required_field_type` (5 parametrized cases) | Skipped scaffold |
| INT-009 | P1 | `TestUniquenessAndNormalization::test_multiple_rows_with_all_optional_refs_null_are_allowed` | Skipped scaffold |
| INT-010 | P1 | `TestUniquenessAndNormalization::test_equivalent_cwd_spellings_collide` (2 parametrized cases) | Skipped scaffold |
| INT-011 | P1 | `TestUniquenessAndNormalization::test_equivalent_bmad_dir_spellings_collide` | Skipped scaffold |
| INT-012 | P1 | `TestUniquenessAndNormalization::test_filesystem_root_remains_root_after_normalization` | Skipped scaffold |
| INT-013 | **P0** | `TestP0BlockingCases::test_semantically_equal_github_references_collide` (2 parametrized cases) | Skipped scaffold |
| INT-014 | P1 | `TestGithubReferenceCanonicalization::test_reject_malformed_github_reference_zero_mutation` (6 parametrized cases) | Skipped scaffold |
| INT-015 | P1 | `TestGithubReferenceCanonicalization::test_valid_github_json_preserved_exactly_with_separate_canonical_key` | Skipped scaffold |
| INT-016 | P1 | `TestProviderIdentityAndFixtureRoundtrip::test_real_provider_fixture_roundtrips_after_restart` (loads the real `status-valid.json` fixture) | Skipped scaffold |
| INT-017 | **P0** | `TestP0BlockingCases::test_reject_partial_provider_identity_zero_mutation` (4 parametrized cases) | Skipped scaffold |
| INT-018 | P1 | `TestProviderIdentityAndFixtureRoundtrip::test_distinct_complete_provider_tuples_are_allowed` | Skipped scaffold |
| INT-019 | **P0** | `TestP0BlockingCases::test_each_uniqueness_dimension_reports_independently` | Skipped scaffold |
| INT-020 | P1 | `TestConflictAggregationAndRetryDiscipline::test_candidate_colliding_on_all_dimensions_reports_all_and_no_row` | Skipped scaffold |
| INT-021 | P1 | `TestConflictAggregationAndRetryDiscipline::test_exact_duplicate_action_conflicts_no_suffix_no_retry` | Skipped scaffold |
| INT-022 | P1 | `TestConflictAggregationAndRetryDiscipline::test_same_identity_values_different_profiles_are_allowed` | Skipped scaffold |
| INT-023 | P1 | `TestConflictAggregationAndRetryDiscipline::test_forced_precheck_miss_still_conflicts_via_real_unique_index` | Skipped scaffold (illustrative private-seam name; self-adjusting `hasattr` guard) |
| INT-024 | P1 | `TestCrossProcessRaces::test_two_processes_race_on_one_identity_one_wins_one_conflicts` (real `multiprocessing.get_context("spawn")` race) | Skipped scaffold |
| INT-025 | P1 | `TestCrossProcessRaces::test_two_processes_create_distinct_identities_both_persist` | Skipped scaffold |
| INT-026 | P1 | `TestProfileIsolation::test_mixed_profile_explicit_db_list_filters_correctly` | Skipped scaffold |
| INT-027 | P1 | `TestProfileIsolation::test_db_path_resolves_under_context_local_profile_home` | Skipped scaffold |
| INT-028 | P1 | `TestProfileIsolation::test_active_profile_stores_correctly_resolver_exception_falls_back_default` | Skipped scaffold |
| INT-029 | P1 | `TestProfileIsolation::test_separate_profile_homes_cannot_read_each_others_bindings` | Skipped scaffold |
| INT-030 | P1 | `TestMigrationAndIdempotentInit::test_reopen_current_schema_twice_without_data_loss_or_error` | Skipped scaffold |
| INT-031 | P1 | `TestMigrationAndIdempotentInit::test_migration_seam_invoked_on_every_connect_including_cached` | Skipped scaffold (self-skips further with an explanatory reason if the migration seam is named differently) |
| INT-032 | P1 | `TestMigrationAndIdempotentInit::test_clear_init_cache_new_process_simulation_preserves_schema` | Skipped scaffold |
| INT-033 | P1 | `TestMigrationAndIdempotentInit::test_concurrent_first_connects_all_close_cleanly` (threaded) | Skipped scaffold |
| INT-034 | P1 | `TestMigrationAndIdempotentInit::test_cached_path_whose_file_is_recreated_does_not_error` | Skipped scaffold |
| INT-035 | P1 | `TestMigrationAndIdempotentInit::test_pragma_relationships_prove_columns_and_unique_predicates` | Skipped scaffold |
| INT-036 | P2 | `TestResourceHygiene::test_connect_closing_closes_connection_on_exit` | Skipped scaffold |
| INT-037 | P1 | `TestJsonUnicodeAndCorruptionHandling::test_nested_unicode_json_null_arrays_survive_exact_roundtrip` | Skipped scaffold |
| INT-038 | P1 | `TestJsonUnicodeAndCorruptionHandling::test_reject_non_serializable_or_non_standard_json_before_insert` (2 parametrized cases) | Skipped scaffold |
| INT-039 | P1 | `TestJsonUnicodeAndCorruptionHandling::test_corrupt_stored_json_fails_explicitly_on_read` | Skipped scaffold |
| INT-040 | P1 | `TestIdentityStability::test_stored_id_not_recomputed_from_changed_input` | Skipped scaffold |
| INT-041 | P1 | `TestIdentityStability::test_forced_random_id_collision_preserves_first_row` | Skipped scaffold (illustrative private id-generator seam name; self-adjusting `hasattr` guard) |
| INT-042 | P1 | `TestFailureInjectionAndRollback::test_injected_insert_failure_rolls_back_zero_row_and_later_reuse_works` | Skipped scaffold |
| INT-043 | P1 | `TestFailureInjectionAndRollback::test_held_immediate_lock_causes_bounded_failure_then_succeeds_after_release` | Skipped scaffold |
| INT-044 | P1 | `TestFailureInjectionAndRollback::test_invalid_parent_path_fails_without_poisoning_cache` | Skipped scaffold |
| INT-045 | P1 | `TestFailureInjectionAndRollback::test_foreign_keys_on_and_journal_mode_wal_or_documented_fallback` | Skipped scaffold |
| VAL-001 | P1 | `test_workflow_commander_contract_validator_passes` (module level, **not** gated by the `hermes_project_work` skip) | **Executable now — already passing** (validates the already-shipped contract package, not this story's implementation) |
| UNIT-001 | P1 | `TestUniquenessAndNormalization::test_path_normalization_matrix` (4 parametrized cases; exercised through create+read since no public path-helper name is committed) | Skipped scaffold |
| UNIT-002 | P1 | Folded into `TestGithubReferenceCanonicalization` (INT-014/015) — no separate public GitHub-key helper name is committed, so canonicalization is observed through create/read+conflict behavior rather than a direct unit call | Skipped scaffold (see class docstring) |
| UNIT-003 | P1 | `TestIdentityStability::test_random_id_format_independent_of_inputs` | Skipped scaffold |

## Reviewer Concern Disposition (carried from TD)

Every reviewer concern in the TD's "Reviewer Concern Disposition" table maps to the same test IDs listed above (e.g. "Random persisted id; never derive identity from cwd/artifacts" → INT-002/INT-040/UNIT-003, now `TestCreateReadRestart::test_new_connection_reads_unchanged_id_and_every_field`, `TestIdentityStability::test_stored_id_not_recomputed_from_changed_input`, `TestIdentityStability::test_random_id_format_independent_of_inputs`). No reviewer concern is left unrepresented.

## Waivers (carried forward from the Test Design doc — no new tests needed; nothing here is newly skipped by this ATDD run)

| Waiver | Reason | Owner | Residual risk | Follow-up trigger |
| --- | --- | --- | --- | --- |
| W-01 Authorization/public caller | Story 2.1a adds an internal repository only; no command/tool wiring in scope. | First public create/read surface owner | A future command/API/tool could expose mutation without authorization. | Any command, API, tool, gateway, or agent action calls this repository — add P0 authorized/unauthorized/cross-profile tests then. |
| W-02 Cwd safety validation | Existence/allowed-root/git-repo checks belong to Story 2.1b. | Story 2.1b owner | Persisted unvalidated cwd data is unsafe if consumed early. | Before any workflow action consumes a binding. |
| W-03 Lifecycle/audit | Update/disable/repair/re-enable/`enabled`/`validation_state`/audit history belong to Story 2.1c. | Story 2.1c owner | No mutable lifecycle evidence exists in this story. | When lifecycle methods are added. |
| W-04 Provider lifecycle/health | Registration/refresh/status/rotation/conflict diagnosis belong to Story 3.2. | Story 3.2 owner | Opaque stored metadata may become stale. | Any provider I/O or status interpretation is introduced. |
| W-05 BMAD mounting | `skills.external_dirs` mutation/mount validation belongs to Story 2.2. | Story 2.2 owner | A stored skill-dir reference is not proof of a usable mount. | Any code mounts or invokes BMAD from this reference. |
| W-06 Async order/cancellation | Synchronous create/read has no queue/event-order/callback-timestamp/retry-loop/cancellation token. | First async binding-operation owner | Later async orchestration could mishandle replay/order/cancellation. | Add events, background work, retries, or cancellation. |
| W-07 External Archon runtime | This story stores a local v1 fixture opaquely; consumes no live provider result. | Provider-integration owner | Local fixtures do not prove real producer compatibility. | Before any provider-dependent story is marked done. |
| W-08 UI/API/E2E and full seed | No public surface exists; unrelated project-work modules are explicitly out of scope. Confirms this ATDD run's "no E2E/Playwright" decision. | Future surface/product owner | User-journey behavior remains untested until a surface exists. | A public surface or another seed module enters scope. |
| W-09 Symlink/Windows case equivalence | Story prescribes textual `abspath + expanduser + trailing-strip`; physical identity undecided. | Architect + Story 2.1b owner | Same physical repo can be represented by aliases. | Physical-path identity approved, Windows CI exposes a collision miss, or Story 2.1b starts. |
| W-10 Performance/scalability SLO | No binding-count/latency/lock-wait/throughput threshold exists. | Product owner + operations | Large stores or heavy contention may regress beyond bounded race checks. | Production contention or an approved scale/SLO requirement appears. |

## Generated Files

- `tests/project_work/__init__.py` — new empty package marker.
- `tests/project_work/test_bindings.py` — 66 pytest test nodes (48 unique test functions, several parametrized): 65 skipped red-phase scaffolds gated on `hermes_project_work.bindings` not existing yet, plus 1 executable contract-validator regression test that already passes.

## Skipped Scaffolds — Why & Activation Trigger

All scaffolds in every class except the standalone contract test share one root cause and one activation trigger:

- **Why skipped:** `hermes_project_work/bindings.py` does not exist (Story 2.1a Task 1 is not implemented yet); importing it raises `ModuleNotFoundError`, so `pb is None` at collection time.
- **What activates them:** implement `hermes_project_work/__init__.py` and `hermes_project_work/bindings.py` per Tasks 1–3 of the story (schema + `connect()`/`connect_closing()`, `create_binding()`, `get_binding()`/`list_bindings_for_profile()`), matching (or intentionally deviating from, with matching test updates) the assumed contract documented at the top of `tests/project_work/test_bindings.py`. Once the import succeeds, `requires_bindings_module`'s `skipif` condition is false and every scaffold in that class runs as a real red/green test.

Three further scaffolds carry an **additional, narrower** self-skip on top of the module-level gate, because they poke at implementation internals whose exact name the story does not pin:

- `TestConflictAggregationAndRetryDiscipline::test_forced_precheck_miss_still_conflicts_via_real_unique_index` — assumes a `_check_uniqueness_dimensions` seam; only patches it if present (`hasattr` guard), otherwise still exercises the real-unique-index fallback path directly.
- `TestIdentityStability::test_forced_random_id_collision_preserves_first_row` — `pytest.skip()`s with an explicit reason if `_new_binding_id` isn't the actual id-generator name; adjust the patched name once Task 3 lands.
- `TestMigrationAndIdempotentInit::test_migration_seam_invoked_on_every_connect_including_cached` — same pattern for `_migrate_add_optional_columns`, which the story text does name explicitly (Task 1, subtask 5), so this one is expected to resolve cleanly once implemented.

## Commands To Run

```bash
# Collect-only sanity check (should show 66 items, no collection errors):
bash scripts/run_tests.sh tests/project_work/test_bindings.py --collect-only -q

# Full run (expected right now: 1 passed, 65 skipped):
bash scripts/run_tests.sh tests/project_work/test_bindings.py -v

# After Task 1-4 implementation lands, the same command should flip to
# real pass/fail results (no more skips) — that transition is the
# TDD green-phase signal for this story.

# Shipped contract validator, run standalone (already green; VAL-001 mirrors this):
cd _bmad-output/planning-artifacts/contracts/workflow-commander && \
  uv run --project ../../../../ python3 validate_contracts.py

# Lint the new test files:
.venv/bin/ruff check tests/project_work/test_bindings.py tests/project_work/__init__.py

# One-time local environment setup if pytest is not yet installed in .venv:
uv sync --extra dev
```

## Next Recommended Workflow

`dev-story` (implement `hermes_project_work/bindings.py` per Tasks 1–3, using this ATDD suite as the red-phase acceptance contract — resolve any place where the assumed contract in the test file's module docstring turns out to differ from the chosen implementation, updating the tests rather than weakening the assertions). Run `bmad-testarch-automate` after implementation to expand coverage beyond this scaffold if needed; `bmad-testarch-trace`/`nfr-assess` remain deferred until execution evidence exists, per the Test Design doc's own Follow-on Workflows section.
