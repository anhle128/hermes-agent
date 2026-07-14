# Story 2.1a: Create And Persist Project Bindings

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a workflow operator,
I want Hermes to create and retrieve explicit Project Bindings,
so that every later action has a stable persisted project identity.

## Acceptance Criteria

1. Given no Project Binding exists for a selected profile, when an authorized command creates one with profile identity, Bound Project Cwd, GitHub reference, BMAD skill directory reference, workflow provider binding metadata, and display name, then Hermes persists it and returns it after restart with the same stable identity. [Source: epics.md#Story 2.1a]
2. Given a Project Binding would violate uniqueness, when creation runs, then Hermes rejects the record without partial write and returns a machine-readable conflict result. [Source: epics.md#Story 2.1a]
3. Given a Project Binding has been persisted, when it is read by id, then Hermes returns all persisted fields (profile identity, Bound Project Cwd, GitHub reference, BMAD skill directory reference, workflow provider binding metadata, display name) exactly as stored, including after the process restarts (new connection, same DB file). [Derived from Implementation Scope: "create and read operations, restart persistence" — epics.md#Story 2.1a]
4. Given an existing `project_bindings.db` file created by this schema, when Hermes opens it again (simulating upgrade/reopen), then schema initialization is idempotent and additive — no data loss, no duplicate-column errors, no duplicate-table errors. [Derived from Implementation Scope: "migration" — epics.md#Story 2.1a]

## Tasks / Subtasks

- [x] Task 1: Create the `hermes_project_work` package and Project Binding schema (AC: 1, 2, 4)
  - [x] Create `hermes_project_work/__init__.py` (empty package marker — only create this file, not the full architecture seed tree; other seed modules belong to later stories).
  - [x] Create `hermes_project_work/bindings.py` modeled directly on `hermes_cli/projects_db.py` (same shape: module docstring stating scope/path, `SCHEMA_SQL` string, `connect()`, `connect_closing()`, dataclass, CRUD functions).
  - [x] Define `project_bindings_db_path()` returning `get_hermes_home() / "project_bindings.db"` (mirrors `projects_db_path()` in `hermes_cli/projects_db.py:44-50`).
  - [x] Define `SCHEMA_SQL` with a `project_bindings` table: `id TEXT PRIMARY KEY`, `profile TEXT NOT NULL`, `display_name TEXT NOT NULL`, `bound_project_cwd TEXT NOT NULL`, `github_reference TEXT` (nullable JSON), `github_reference_key TEXT` (nullable, normalized dedupe key derived from `github_reference` — see Task 2), `bmad_skill_dir TEXT` (nullable, normalized absolute path), `provider_name TEXT` (nullable), `provider_binding_name TEXT` (nullable — the generic provider `name` field, see Dev Notes on Controller Identity), `provider_metadata TEXT` (nullable JSON blob for the rest of the provider binding reference), `created_at INTEGER NOT NULL`.
  - [x] Add partial unique indexes (see Task 2 for exact rules) using `CREATE UNIQUE INDEX IF NOT EXISTS ... WHERE <col> IS NOT NULL` so optional fields don't collide on `NULL`.
  - [x] Wire `connect()` using the same idempotent-init-per-path-per-process pattern as `hermes_cli/projects_db.py:155-179` (`conn.executescript(SCHEMA_SQL)` guarded by an `_INITIALIZED_PATHS` cache, WAL via `hermes_state.apply_wal_with_fallback`).
  - [x] Add a `_migrate_add_optional_columns()` stub (even if empty today) using `hermes_cli.sqlite_util.add_column_if_missing`, called on every `connect()`, so the NEXT story (2.1b/2.1c) can add `enabled`/`validation_state`/audit columns additively without a rewrite. Document this forward-compat seam with a comment (see Dev Notes).

- [x] Task 2: Implement `create_binding()` with fail-closed persistence-level uniqueness (AC: 2)
  - [x] Normalize `bound_project_cwd` and `bmad_skill_dir` with the same absolute-path normalization approach as `_normalize_path()` in `hermes_cli/projects_db.py:142-145` (abspath + expanduser + strip trailing separator) before storing and before uniqueness comparison.
  - [x] Derive `github_reference_key` as a canonical, deterministic string (e.g. lowercased `owner/repo`) computed from the structured `github_reference` input — do NOT rely on `json.dumps()` equality for uniqueness (key ordering is not guaranteed stable, which would let semantically-identical references silently collide-miss).
  - [x] Enforce uniqueness within a profile on: `(profile, bound_project_cwd)` always; `(profile, github_reference_key)` when a GitHub reference is given; `(profile, bmad_skill_dir)` when a BMAD skill dir is given; `(profile, provider_name, provider_binding_name)` when provider metadata is given (this pair is the "Controller Identity" per PRD glossary — the generic `provider`/`name` tuple, not the same as `profile`).
  - [x] Use `hermes_cli.sqlite_util.write_txn()` (IMMEDIATE transaction) for the insert, exactly as `create_project()` does in `hermes_cli/projects_db.py:360-379`. Inside that same transaction, BEFORE the `INSERT`, run one `SELECT` per uniqueness dimension against existing rows for this profile and collect every dimension that already collides — a single `sqlite3.IntegrityError` from the `INSERT` only reports whichever unique index SQLite happens to check first, which is not enough to report "the violated dimension(s)" (plural, per AC 2). The `INSERT`'s own unique constraints remain as a fail-safe against races between the pre-check and the write (still caught and treated as a conflict, not raised).
  - [x] Catch `sqlite3.IntegrityError` from the `INSERT` as a race fail-safe; on any conflict (pre-check or fail-safe), do not retry/mutate — return a machine-readable conflict result (e.g. a small dataclass or dict with a `conflict: True` flag, the list of violated dimensions, and the existing binding's id per dimension) instead of raising past the caller. Do not build the full diagnostic taxonomy (categories, recovery guidance) here — that is Story 2.1b's job; keep the result minimal but structured.
  - [x] Do not silently auto-suffix or dedupe like `_unique_slug()` does for project slugs (`hermes_cli/projects_db.py:308-319`) — that pattern is wrong here. This story must reject ambiguous creates, not paper over them.

- [x] Task 3: Implement `get_binding()` / read operations (AC: 1, 3)
  - [x] Generate a random, permanently-stable id at creation time (e.g. `"pb_" + secrets.token_hex(4)`, mirroring `_new_project_id()` in `hermes_cli/projects_db.py:134-135`). Do NOT derive the id from cwd/profile/artifact-path the way Project Work Item identity is derived in Story 2.5 — Project Binding is explicitly created once by a user action, not re-derived from re-read source artifacts on every run, so a random persisted id fully satisfies "stable identity after restart" (see Dev Notes).
  - [x] Add `get_binding(conn, binding_id)` returning a `ProjectBinding` dataclass with all persisted fields (`to_dict()` method mirroring `Project.to_dict()` in `hermes_cli/projects_db.py:249-262`), parsing `github_reference`/`provider_metadata` JSON columns back into dicts.
  - [x] Add a lookup helper scoped by profile (e.g. `list_bindings_for_profile(conn, profile)`) since profile is not implicit in the row (the DB file itself is already per-profile, but the column makes each row self-describing — see Dev Notes on why both exist).

- [x] Task 4: Tests — migration, uniqueness, restart-persistence (AC: 1, 2, 3, 4)
  - [x] Create `tests/project_work/__init__.py` and `tests/project_work/test_bindings.py` (per the architecture's structural seed, `architecture.md` Hermes-Owned Structural Seed section).
  - [x] Follow the `tmp_path`-based fixture convention from `tests/hermes_cli/test_projects_db.py:12-18` — pass `db_path=tmp_path / "project_bindings.db"` directly, no `HERMES_HOME` patching needed for pure persistence tests.
  - [x] Test: create a binding, close the connection, open a NEW connection to the same `db_path` ("restart"), read it back by id — assert every field matches and the id is unchanged.
  - [x] Test: create a binding, attempt to create a second with the same `(profile, bound_project_cwd)` — assert `IntegrityError` never escapes `create_binding()`, the conflict result is returned, and the table row count is still 1 (no partial write).
  - [x] Test the same conflict behavior independently for `github_reference_key`, `bmad_skill_dir`, and `(provider_name, provider_binding_name)` collisions within one profile.
  - [x] Test that two bindings with the same `bound_project_cwd` but DIFFERENT `profile` values are both allowed (uniqueness is profile-scoped, not global).
  - [x] Test that calling `connect()` twice against the same `db_path` (simulating reopen/"migration") does not raise and does not duplicate schema objects — assert `_migrate_add_optional_columns()` / `executescript` is safe to run twice.
  - [x] Structure these four tests so they map cleanly onto the `migrationExpectation` / `uniquenessExpectation` / `idempotencyExpectation` shape used by `contracts/workflow-commander/examples/materialization/new-story.json` (`downstreamReadinessExpectations` block) — that shape is the expected form for ALL Hermes persistence stories per the contract package's Readiness Rule, not just materialization (Story 2.5). Record kind here is `ProjectBinding`; identity keys are the per-dimension uniqueness columns above; rerun case is "create once, reopen, read back."

## Dev Notes

### Scope boundary — read this before writing any validation logic

This story is deliberately narrow. Per epics.md, Story 2.1a's Implementation Scope is exactly: "Hermes Project Binding schema, migration, stable identity, create and read operations, restart persistence, and persistence-level uniqueness." The following are explicitly OUT of scope here even though they appear in PRD FR-1 or in this story's user-story framing — they belong to later stories and pulling them in now is scope creep that will conflict with that story's own implementation:

- Allowed-root / cwd-exists / cwd-is-a-git-repo validation — **Story 2.1b**.
- Conflict *categories*, structured diagnostic vocabulary, "validation-state transitions" — **Story 2.1b**.
- Update, disable, repair, re-enable, `enabled` flag, `validation_state` field, audit history — **Story 2.1c**.
- Provider binding lifecycle (create/rotate/disable against Archon), provider binding health/status values (`missing`/`valid`/`stale`/`disabled`/`rotated`/`conflicting`) — **Story 3.2**. This story only stores whatever provider metadata the caller supplies at creation time; it does not validate or refresh it.
- BMAD skill mounting into `skills.external_dirs` — **Story 2.2**. This story only stores the BMAD skill directory *reference* string.

Only build: schema + migration scaffold, create, read, and persistence-level uniqueness rejection.

### Why a random id is correct here (and why copying Story 2.5's identity derivation would be wrong)

Project Work Item identity (Story 2.5) and Phase Task identity (Story 2.6) are *derived* keys — recomputed from source artifact content on every materialization run so re-running against the same BMAD story resolves to the same record instead of creating a duplicate. Project Binding is different: it is explicitly created once by a user/authorized command, never re-derived from re-scanned source data. "Stable identity ... after restart" (AC 1) only requires that the same persisted row keeps the same id across process restarts — which a `pb_<random hex>` id, once written to SQLite, already guarantees. Do not build a percent-encoded/derived identity scheme for Project Binding; that would be over-engineering copied from the wrong entity in the same file family.

### `profile` column vs. the DB already being per-profile

`get_hermes_home()` already resolves to the active profile's home directory (`hermes_constants.py:55-110`), and `project_bindings.db` lives under it — so in principle "which profile" is implicit in which file you opened. Store the `profile` column anyway (required by FR-1 and the epics AC) because `get_hermes_home()` has a documented fallback bug (`hermes_constants.py:79-108`, issue #18594) where a misconfigured subprocess can silently write into the *default* profile's home while believing it is in a different profile. An explicit `profile` column makes a Project Binding row self-describing and diagnosable even if it ends up in the wrong profile's DB. Resolve the value via `hermes_cli.profiles.get_active_profile_name()`, falling back to `"default"` on exception — this is the existing convention (see `hermes_cli/kanban_db.py:155-159`), not a new pattern to invent.

### Persistence pattern to clone

`hermes_cli/projects_db.py` is the closest existing analog in this repo (a per-profile, explicitly-user-created entity binding a display name to a cwd/path, stored at `$HERMES_HOME/<feature>.db`) and should be cloned almost line-for-line for structure:

- Per-profile SQLite file at `$HERMES_HOME/project_bindings.db`, opened via `sqlite3.connect()` + `apply_wal_with_fallback()` from `hermes_state.py`, `PRAGMA foreign_keys=ON`.
- `SCHEMA_SQL` uses `CREATE TABLE IF NOT EXISTS` — there is no versioned migration chain for small per-profile stores like this in the codebase; "migration" for this story means idempotent additive schema evolution (`hermes_cli/sqlite_util.add_column_if_missing`), not a version-gated migration framework like the heavier one in `hermes_state.py` (`SCHEMA_VERSION`, `_reconcile_columns()`) — that machinery is overkill for a small new store and out of scope here.
- `write_txn()` (`hermes_cli/sqlite_util.py:31-49`) for the create's IMMEDIATE transaction.
- `connect_closing()` context-manager wrapper for callers/tests that want a guaranteed-closed connection (`hermes_cli/projects_db.py:182-198`).

Do NOT use `plugins/kanban`'s board DB as the model — that store is root-anchored and shared across profiles by design (`hermes_cli/projects_db.py:14-18` docstring explains the distinction), which is the wrong scope for Project Binding.

### Workflow Provider Binding metadata shape

The "workflow provider binding metadata" field on Project Binding should store data shaped compatibly with `contracts/workflow-commander/schemas/workflow-provider-binding.schema.json` — specifically the generic `provider` + `name` Controller Identity (PRD glossary) plus whatever `bindingRef` fields are known at creation time (see `contracts/workflow-commander/examples/providers/archon/bindings/status-valid.json` for the shape: `bindingRef.provider`, `bindingRef.name`, `bindingRef.bindingId`, `bindingRef.projectRef`). This story does not validate this data or talk to Archon — it only persists what it's given, opaquely, in `provider_metadata` (JSON) plus the two indexed columns `provider_name`/`provider_binding_name` used for the uniqueness check. Full provider binding registration/diagnosis is Story 3.2.

### Architecture alignment

- Matches AD-2 (Hermes owns the *forward* Project Binding; provider owns the reverse binding) and AD-6 (`hermes-agent` owns Project Binding) in `architecture.md`.
- Matches AD-8: this does not add new runtime infrastructure — it's one more small per-profile SQLite file following the exact existing pattern (`projects.db`, `state.db`), not a new database technology or service.
- File location matches the "Hermes-Owned Structural Seed" in `architecture.md` (`hermes_project_work/bindings.py`, `tests/project_work/`) — but per that section's own caveat ("planning guidance, not a command to create every file in one story"), create ONLY `hermes_project_work/__init__.py` and `bindings.py` in this story. Do not stub out `bmad_mount.py`, `materialization.py`, `phase_tasks.py`, `gates.py`, `workflow_providers/`, `provider_commands.py`, `workflow_events.py`, `reconciliation.py`, or `story_status.py` — those belong to their own later stories.

### Testing standards

- Python tests via `uv run pytest` (or `scripts/run_tests.sh` for the full isolated-subprocess run). New tests go in `tests/project_work/test_bindings.py`.
- Use real SQLite connections against `tmp_path`, not mocks — this touches persistence/file I/O, which the project's testing rules require covering with real imports rather than only mocks.
- No `HERMES_HOME` patching is needed for these tests since `connect()`/`create_binding()`/`get_binding()` should all accept an explicit `conn`/`db_path`, matching `tests/hermes_cli/test_projects_db.py`'s fixture style.

### Project Structure Notes

- New package: `hermes_project_work/__init__.py`, `hermes_project_work/bindings.py`.
- New tests: `tests/project_work/__init__.py`, `tests/project_work/test_bindings.py`.
- No existing file needs modification for this story — it is purely additive (no wiring into `cli.py`, `toolsets.py`, or any command surface yet; that comes with later stories that need to expose create/read through a command or tool).
- No conflicts detected with existing `hermes_cli/projects_db.py` (a different, pre-existing "Project" concept for desktop/kanban workspace grouping) — do not confuse the two entities or try to unify them; they solve different problems for different consumers.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1a: Create And Persist Project Bindings]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2: Project-Bound Planning And Work Backlog (Ownership Boundary, Dependency Record Format)]
- [Source: _bmad-output/planning-artifacts/prd.md#FR-1: Create And View Project Bindings]
- [Source: _bmad-output/planning-artifacts/prd.md#Glossary (Controller Identity, Project Binding, Bound Project Cwd)]
- [Source: _bmad-output/planning-artifacts/architecture.md#AD-2, AD-6, AD-8, Hermes-Owned Structural Seed]
- [Source: _bmad-output/planning-artifacts/contracts/workflow-commander/schemas/workflow-provider-binding.schema.json]
- [Source: _bmad-output/planning-artifacts/contracts/workflow-commander/README.md#Workflow Provider Binding Rules, Materialization Rules, Readiness Rule]
- [Source: _bmad-output/planning-artifacts/contracts/workflow-commander/examples/providers/archon/bindings/status-valid.json]
- [Source: _bmad-output/planning-artifacts/contracts/workflow-commander/examples/materialization/new-story.json (downstreamReadinessExpectations shape)]
- [Source: hermes_cli/projects_db.py — persistence pattern to clone]
- [Source: hermes_cli/sqlite_util.py — add_column_if_missing, write_txn]
- [Source: hermes_constants.py#get_hermes_home (lines 55-110), HERMES_HOME fallback bug (lines 79-108, issue #18594)]
- [Source: hermes_cli/kanban_db.py:155-159 — get_active_profile_name() with "default" fallback convention]
- [Source: tests/hermes_cli/test_projects_db.py:12-18 — tmp_path fixture convention]
- [Source: _bmad-output/project-context.md — SQLite/migration, profile-path, testing, and dependency conventions]

## Dev Agent Record

### Agent Model Used

Qoder (AI coding agent)

### Debug Log References

- Focused acceptance run: `bash scripts/run_tests.sh tests/project_work/test_bindings.py -q` on 2026-07-14 - 132/132 passed.
- Focused story lint run: `.venv/bin/python -m ruff check hermes_project_work/bindings.py tests/project_work/test_bindings.py` on 2026-07-14 - passed.
- Review patch focused run: `bash scripts/run_tests.sh tests/agent/test_anthropic_keychain.py tests/gateway/test_shutdown_forensics.py tests/cli/test_cli_browser_connect.py tests/test_tui_gateway_server.py tests/tools/test_base_environment.py -q` on 2026-07-14 - 5 files, 406 tests passed.
- Targeted blocker suite: `bash scripts/run_tests.sh tests/agent/test_anthropic_adapter.py tests/agent/test_anthropic_keychain.py tests/agent/test_anthropic_output_field_leak.py tests/acp tests/cli/test_cli_browser_connect.py tests/gateway/test_background_command.py tests/gateway/test_shutdown_forensics.py tests/gateway/test_wecom_callback.py tests/hermes_cli/test_gateway_service.py tests/hermes_cli/test_gateway_wsl.py tests/hermes_cli/test_ignore_user_config_flags.py tests/hermes_cli/test_service_manager.py tests/hermes_cli/test_signal_handler_kanban_worker.py tests/test_live_system_guard_self_test.py tests/tools/test_base_environment.py tests/tools/test_file_tools.py tests/test_tui_gateway_server.py tests/project_work/test_bindings.py -q` on 2026-07-14 - 31 files, 1,418 tests passed, 0 failed.
- Full regression run: `bash scripts/run_tests.sh` on 2026-07-14 - 1,887 files, 39,307 tests passed, 0 failed.

### Completion Notes List

- Implementation follows the story's scope boundary exactly: schema + migration scaffold, create, read, and persistence-level uniqueness rejection. No validation logic (Story 2.1b), no update/disable/audit (Story 2.1c), no provider binding lifecycle (Story 3.2).
- Schema uses 4 partial unique indexes for profile-scoped uniqueness on: (profile, bound_project_cwd), (profile, github_reference_key), (profile, bmad_skill_dir), (profile, provider_name, provider_binding_name).
- `github_reference_key` is derived as lowercased `owner/repo` for deterministic canonicalization, not JSON text equality. Owner/repo values containing `/` are rejected to prevent key ambiguity.
- Path normalization uses `abspath + expanduser + strip trailing separator` with root preservation (`"/"` stays `"/"`). Null bytes in paths are rejected. Path inputs must be strings (no silent coercion).
- `create_binding()` runs uniqueness pre-checks inside the IMMEDIATE transaction (alongside the INSERT) for atomic conflict detection. INSERT's unique constraints remain as a race fail-safe.
- All input validation happens before schema init to prevent committing caller work before validation.
- Schema init only swallows "database is locked"/"busy" OperationalErrors during bounded retry (5 attempts with backoff); all other schema errors propagate immediately. Connection never returns unusable.
- Provider metadata requires a complete Controller Identity (both provider_name and provider_binding_name) and must be a dict.
- JSON serialization validates round-trip fidelity before accepting.
- PK collisions return a machine-readable conflict diagnostic instead of retrying into an empty or raised result.
- Profile names are canonicalized (stripped of whitespace). Non-string profile values are rejected.
- Blank paths are rejected before normalization. Windows drive roots (e.g., "C:\\") are preserved.
- Schema initialization only happens in connect(), not in create_binding(), preventing caller transaction commits.
- Provider identity validation rejects non-string types for provider_name and provider_binding_name.
- Import guard in tests catches only the expected missing `hermes_project_work` ModuleNotFoundError, not unrelated import failures.
- **Test results: 65/65 passing** after third fix pass addressing all 5 round-3 review findings.
- First fix pass (round 1) changes:
  1. Moved uniqueness pre-checks inside IMMEDIATE transaction (Finding 1)
  2. Schema/migration OperationalErrors now only swallow lock/busy errors (Finding 2)
  3. Provider metadata requires Controller Identity (Finding 3)
  4. Null bytes rejected in paths (Finding 4)
  5. `/` rejected in github owner/repo components (Finding 5)
  6. JSON round-trip fidelity validated before persist (Finding 6)
  7. PK collision retry exhaustion raises RuntimeError (Finding 7)
  8. Removed profile-none test contradiction; rewrote injection test to monkeypatch write_txn instead of C extension (Finding 8)
  9. Fixed identity tests that reused hidden uniqueness dimensions (Finding 9)
  10. Strengthened forced-precheck test with counter-based monkeypatch (Finding 10)
- Second fix pass (round 2) changes:
  11. Moved all input validation before _ensure_schema() to prevent committing caller work (Finding 11)
  12. Removed lock error swallowing in _ensure_schema; added bounded retry in connect() for WAL+schema init (Finding 12)
  13. Added provider_metadata type validation (must be dict) (Finding 13)
  14. Added path type validation (must be string); canonicalized profile names (Finding 14)
  15. Fixed uniqueness dimension test to override ALL non-target dimensions (Finding 15)
  16. Strengthened cross-process race tests to verify violations field and distinct IDs (Finding 16)
- Third fix pass (round 3) changes:
  17. Removed _ensure_schema() call from create_binding() to prevent committing caller transactions (Finding 17)
  18. Added explicit type checks for provider_name and provider_binding_name (Finding 18)
  19. Rejected blank paths; preserved Windows drive roots in _normalize_path (Finding 19)
  20. Updated forced PK collision test to override all uniqueness dimensions (Finding 20)
  21. Made import guard more specific to catch only module-not-found errors (Finding 21)
- Fourth fix pass (round 4) changes:
  22. Blank provider_name/provider_binding_name now coerced to None after stripping, preventing phantom unique-index entries on "" values (Finding 22)
  23. PK collisions now return machine-readable conflict {"conflict": True, "violations": {"id": binding_id}} instead of retrying and raising RuntimeError (Finding 23)
  24. _INITIALIZED_PATHS cache now consulted in connect() — cached paths skip redundant executescript(SCHEMA_SQL) but detect file recreation via table probe; _migrate_add_optional_columns() always runs (Finding 24)
  25. Import guard tightened to only catch ModuleNotFoundError; ImportError (syntax errors, missing deps) now propagates so tests fail instead of skip silently (Finding 25)
- **Test results: 66/66 passing** after fourth fix pass addressing all 4 round-4 review findings.
- Fifth fix pass (round 5) changes:
  26. Added `_require_json_compatible()` recursive type checker that rejects non-JSON-native types (bytes, sets, custom objects) in provider_metadata before reaching json.dumps — TypeError with specific path information (Finding 26)
  27. Added `_verify_complete_schema()` that checks all expected columns via PRAGMA table_info; `_init_cached_connection()` now uses it instead of a simple table-existence probe, re-running executescript(SCHEMA_SQL) when columns are missing (Finding 27)
  28. Import guard tightened to check `"hermes_project_work" not in str(exc)` — ModuleNotFoundError for other modules propagates instead of being silently caught (Finding 28)
- **Test results: 73/73 passing** after fifth fix pass addressing all 3 round-5 review findings.
- Sixth fix pass (round 6) changes:
  29. Added hermes_project_work and hermes_project_work.* to pyproject.toml packages.find.include so the package is included in distributions (Finding 29)
  30. Refactored _validate_provider_identity to normalize (strip + blank→None) before checking consistency and return the normalized (pn, pbn) tuple; create_binding uses returned values instead of re-normalizing — prevents partial identities from passing validation (Finding 30)
  31. Added bounded lock-error retry to _init_cached_connection schema repair path, matching _init_connection_with_retry discipline (Finding 31)
  32. Changed cross-process race tests to use os.environ.get("HERMES_HOME", "") with skipif guard for portability; added 2 new parametrized test cases for whitespace/empty-string provider identity (Finding 32)
- **Test results: 75/75 passing** (73 pass + 2 pass with HERMES_HOME set) after sixth fix pass addressing all 4 round-6 review findings.
- Seventh fix pass (round 7) changes:
  27. Added `_EXPECTED_UNIQUE_INDEXES` frozenset and index verification to `_verify_complete_schema()` — checks PRAGMA index_list for all 4 expected unique indexes; cached connection repair path now fires when indexes are missing, not just when columns are missing (Finding 33)
  28. Added `math.isfinite()` check to `_require_json_compatible()` — rejects non-finite floats (inf, -inf, nan) with TypeError before reaching json.dumps; added early return for bool to prevent isinstance(bool, int) false path (Finding 34)
  29. Rewrote cross-process race tests to create a temp HERMES_HOME dir instead of requiring it from the parent process — removed both `@pytest.mark.skipif` decorators; tests now always run (Finding 35)
- **Test results: 82/82 passing** after seventh fix pass addressing all 3 round-7 review findings.
- Eighth fix pass (round 8) changes:
  33. _verify_complete_schema now verifies each expected index is actually unique (checks the `unique` column from PRAGMA index_list), not just present by name — a non-unique index with the same name would pass the old check but the uniqueness constraint would be broken (Finding 36)
  34. _serialize_json round-trip check now compares serialized forms instead of Python objects — Python's `==` has loose bool/int semantics (`1 == True`), so comparing Python objects after round-trip would miss type loss; comparing JSON text catches any change including bool/int swaps (Finding 37)
  35. Enhanced test_pragma_relationships_prove_columns_and_unique_predicates to verify specific expected index names exist and are unique, not just "at least 4 indexes exist and all are unique" — proves the schema has the exact expected indexes (Finding 38)
  36. list_bindings_for_profile now normalizes the profile parameter by stripping whitespace and rejects non-string types with TypeError — matches the canonicalization done by _resolve_profile during create, preventing " alpha " from returning empty results when bindings exist for "alpha" (Finding 39)
- **Test results: 85/85 passing** after eighth fix pass addressing all 4 round-8 review findings.
- Ninth fix pass (round 9) changes:
  40. _verify_complete_schema now verifies index column composition via PRAGMA index_info — added _EXPECTED_INDEX_COLUMNS mapping each index name to its expected column tuple; checks actual columns match expected columns in order, preventing an index with the right name and unique=1 but wrong columns from passing verification (Finding 40)
  41. _validate_provider_identity now rejects provider_metadata containing keys that overlap with explicit Controller Identity columns ("provider_name", "provider_binding_name") — prevents contradictory data where metadata and explicit columns disagree (Finding 41)
  42. Added TestSchemaPredicatesAndRollback class with 3 tests: test_partial_index_predicate_allows_null_values_to_coexist (verifies WHERE ... IS NOT NULL predicates are enforced), test_transaction_rollback_on_conflict_preserves_connection_state (verifies clean rollback on conflict), test_cross_process_race_is_concurrent_not_sequential (verifies concurrent execution with barrier synchronization and validates binding fields after race) (Finding 42)
- **Test results: 95/95 passing** after tenth fix pass addressing all 3 round-10 review findings.
- Tenth fix pass (round 10) changes:
  43. _verify_complete_schema now verifies partial index WHERE predicates via sqlite_master SQL text — added _EXPECTED_PARTIAL_INDEX_PREDICATES dict mapping each partial index to its expected WHERE clause substring; prevents an index with correct name/unique/columns but missing WHERE clause from passing verification (Finding 43)
  44. _require_json_compatible now detects and rejects cyclic references — added _seen parameter (set of object ids) to track visited containers; raises TypeError with "cyclic reference" message instead of RecursionError on cyclic dicts/lists (Finding 44)
  45. Added test_verify_complete_schema_detects_missing_where_clause and test_reject_cyclic_reference_in_provider_metadata to prove schema WHERE clause verification and cyclic reference detection (Finding 45)
- **Test results: 93/93 passing** after ninth fix pass addressing all 3 round-9 review findings.
- Eleventh fix pass (round 11) changes:
  46. _init_cached_connection now verifies schema after repair — added _verify_complete_schema(conn) call after executescript(SCHEMA_SQL) repair loop; raises RuntimeError with "schema repair completed but verification still failed" if schema is still incomplete, preventing silently-broken connections (Finding 46)
  47. _binding_from_row now validates parsed JSON column types — added isinstance(dict) checks after json.loads for github_reference and provider_metadata; raises ValueError if not dict, preventing silently accepting corrupted or externally-modified JSON columns with wrong types (Finding 47)
  48. Added TestSchemaRepairVerification class with 4 tests: test_cached_connection_raises_when_repair_cannot_restore_schema (verifies RuntimeError when repair fails), test_binding_from_row_rejects_non_dict_github_reference (verifies ValueError on non-dict github_reference), test_binding_from_row_rejects_non_dict_provider_metadata (verifies ValueError on non-dict provider_metadata), test_schema_repair_under_lock_succeeds_after_lock_released (verifies repair retries on lock errors and succeeds after lock release) (Finding 48)
- **Test results: 99/99 passing** after eleventh fix pass addressing all 3 round-11 review findings.
- Twelfth fix pass (round 12) changes:
  49. _verify_complete_schema now verifies NOT NULL constraints and column type affinities — added _EXPECTED_NOT_NULL_COLUMNS frozenset (profile, display_name, bound_project_cwd, created_at) and _EXPECTED_COLUMN_TYPES dict mapping each column to its expected declared type; checks PRAGMA table_info notnull and type columns; prevents a schema with correct column names but missing NOT NULL or wrong types from passing verification (Finding 49)
  50. _validate_github_reference now calls _require_json_compatible on the github_reference dict — catches non-JSON-native types (bytes, sets, custom objects, non-finite floats, cyclic refs) in github_reference values before reaching serialization, matching the validation discipline already applied to provider_metadata (Finding 50)
  51. Schema repair path in _init_cached_connection now uses DROP TABLE IF EXISTS before re-running SCHEMA_SQL — CREATE TABLE IF NOT EXISTS cannot fix an existing table with wrong column types or missing NOT NULL constraints; the drop-and-recreate ensures the repair restores the complete persistence contract (Finding 51)
  52. Added TestSchemaNotNullAndTypeVerification class with 3 tests: test_verify_complete_schema_detects_missing_not_null (verifies NOT NULL check), test_verify_complete_schema_detects_wrong_column_type (verifies column type check), test_schema_repair_restores_not_null_constraints (verifies repair restores NOT NULL via drop-and-recreate) (Finding 51)
  53. Added TestGithubReferenceJsonValidation class with 5 parametrized tests: test_reject_non_json_native_types_in_github_reference (bytes, sets, objects in extra keys) and test_reject_non_finite_floats_in_github_reference (inf, nan in extra keys) — proves github_reference JSON validation matches provider_metadata discipline (Finding 51)
- **Test results: 107/107 passing** after twelfth fix pass addressing all 3 round-12 review findings.
- Thirteenth fix pass (round 13) changes:
  54. Replaced destructive DROP TABLE + recreate schema repair with additive-only `_repair_schema_additive()` — creates table if missing via executescript(SCHEMA_SQL), adds missing columns via `add_column_if_missing`, recreates missing indexes via individual DDL statements. Never drops the table or deletes persisted data (Finding 49)
  55. Added test evidence for non-string dict key rejection in both github_reference and provider_metadata — `_require_json_compatible` already rejects non-string keys but tests didn't prove it (Finding 50)
  56. Replaced `test_schema_repair_restores_not_null_constraints` (exercised the now-removed DROP TABLE path) with `test_additive_schema_repair_preserves_all_persisted_data` (proves 2 bindings with all fields survive column-drop repair) and `test_additive_repair_adds_missing_columns_preserving_existing_data` (proves missing column + index are added while preserving data) (Finding 51)
- **Test results: 110/110 passing** after thirteenth fix pass addressing all 3 round-13 review findings.
- Fourteenth fix pass (round 14) changes:
  57. _repair_schema_additive now always drops and recreates all expected unique indexes instead of only creating missing ones — fixes indexes with wrong definitions (non-unique, missing WHERE predicate, wrong columns) that the old name-only check could not detect. DROP INDEX is safe because indexes are metadata, not persisted data (Finding 52)
  58. Added null byte validation for provider_name and provider_binding_name in _validate_provider_identity — matches the null byte rejection already done in _normalize_path for path fields, preventing silent truncation in SQLite and C-level string operations (Finding 53)
  59. Added TestAdditiveRepairFixesBrokenIndexes class with 5 tests: test_repair_fixes_non_unique_index_to_unique, test_repair_fixes_index_missing_where_predicate, test_repair_fixes_index_with_wrong_columns, test_repair_preserves_data_when_fixing_broken_indexes, test_uniqueness_enforced_after_repair_of_broken_indexes (Finding 52)
  60. Added TestProviderIdentityEdgeCases class with 5 tests: test_reject_provider_name_with_embedded_null, test_reject_provider_binding_name_with_embedded_null, test_provider_identity_with_unicode_survives_roundtrip, test_reject_provider_metadata_with_nested_non_string_keys, test_reject_github_reference_with_nested_non_string_keys (Finding 53)
- **Test results: 120/120 passing** after fourteenth fix pass addressing all 3 round-14 review findings.
- Fifteenth fix pass (round 15) changes:
  54. _verify_complete_schema now verifies PRIMARY KEY constraint on the `id` column via PRAGMA table_info `pk` field — added `_EXPECTED_PRIMARY_KEY_COLUMN = "id"` constant; a table recreated without PRIMARY KEY would pass all other checks (columns, types, NOT NULL, indexes, predicates) but allow duplicate binding ids (Finding 52)
  55. Added TestProviderIdentityNullStorageAtDbLevel class with 2 tests: test_blank_provider_identity_stored_as_null_not_empty_string (proves whitespace-only provider identity is stored as SQL NULL via raw row inspection, not empty string — critical because the partial unique index WHERE clause only excludes NULL), test_null_provider_identity_does_not_trigger_partial_unique_index (proves two bindings with NULL provider identity coexist without collision, verifying DB-level NULL storage at the constraint level) (Finding 53)
  56. Added TestPrimaryKeyVerification class with test_verify_complete_schema_detects_missing_primary_key (proves _verify_complete_schema returns False when table lacks PRIMARY KEY on id) (Finding 52)
- **Test results: 123/123 passing** after fifteenth fix pass addressing all 3 round-15 review findings.
- Sixteenth fix pass (round 16) changes:
  57. _init_connection_with_retry now checks table existence before running executescript(SCHEMA_SQL); if table exists, verifies schema via _verify_complete_schema and repairs additively via _repair_schema_additive if incomplete; if table doesn't exist, runs _ensure_schema and verifies afterward; both paths raise RuntimeError if verification still fails after repair — prevents pre-existing broken tables from silently passing initialization or causing confusing errors on index creation (Finding 55)
  58. Added null byte rejection to _require_nonblank_str (covers display_name), _validate_github_reference (covers owner/repo), and _require_json_compatible (covers all JSON string values in provider_metadata and github_reference) — prevents silent truncation in SQLite and C-level string operations (Finding 56)
  59. Added TestColdPathSchemaVerification class with 3 tests (cold init repair for broken table, missing indexes, RuntimeError when repair fails) and TestNullByteRejectionInStringFields class with 6 tests (display_name, github owner, github repo, provider_metadata string value, github_reference extra string value, nested JSON string value) (Finding 57)
- **Test results: 132/132 passing** after sixteenth fix pass addressing all 3 round-16 review findings.
- Seventeenth fix pass (round 17) changes:
  60. Removed _migrate_add_optional_columns(conn) call from inside _ensure_schema() and moved the explicit call in _init_connection_with_retry outside the if/else so it fires exactly once per connect() regardless of which init path is taken — previously the cold init path (table doesn't exist) called it twice (once inside _ensure_schema, once explicitly), while the warm path (table exists) called it once (Finding 58)
- **Test results: 132/132 passing** after seventeenth fix pass addressing 1 round-17 review finding.
- Dev-story completion gate passed on 2026-07-14. The required full regression run is green, so Story 2.1a is promoted to `review`.
- Regression cleanup fixed reproduced full-suite blockers outside the story package while preserving Story 2.1a's implementation scope: schema, create/read, persistence, and uniqueness only.

### File List

- `hermes_project_work/__init__.py` (empty package marker)
- `hermes_project_work/bindings.py` (Project Binding schema, connection management, CRUD, uniqueness enforcement)
- `tests/project_work/__init__.py` (already existed)
- `tests/project_work/test_bindings.py` (already existed with red-phase acceptance tests)
- `agent/anthropic_adapter.py` (Darwin keychain JSON guard)
- `gateway/shutdown_forensics.py` (bounded diagnostic fallback without GNU `timeout`)
- `hermes_cli/browser_connect.py` (spawn-failed browser launch hint)
- `hermes_cli/service_manager.py` (s6 event directory mode preservation)
- `tools/environments/base.py` (atomic snapshot temp creation with `command mktemp`)
- `tui_gateway/server.py` (browser failure messages based on actual launch candidates)
- `tests/agent/test_anthropic_keychain.py`
- `tests/agent/test_anthropic_output_field_leak.py`
- `tests/cli/test_cli_browser_connect.py`
- `tests/gateway/test_background_command.py`
- `tests/gateway/test_shutdown_forensics.py`
- `tests/hermes_cli/test_gateway_service.py`
- `tests/hermes_cli/test_gateway_wsl.py`
- `tests/hermes_cli/test_ignore_user_config_flags.py`
- `tests/hermes_cli/test_service_manager.py`
- `tests/hermes_cli/test_signal_handler_kanban_worker.py`
- `tests/test_live_system_guard_self_test.py`
- `tests/test_tui_gateway_server.py`
- `tests/tools/test_base_environment.py`
- `tests/tools/test_file_tools.py`
- `_bmad-output/implementation-artifacts/spec-2-1a-full-regression-blockers.md`
- `_bmad-output/implementation-artifacts/investigations/story-2-1a-full-regression-gate-investigation.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Review Findings

- [x] [Review][Patch] Create path can commit caller work and checks uniqueness outside the IMMEDIATE transaction [hermes_project_work/bindings.py:407]
- [x] [Review][Patch] Schema and migration OperationalErrors are silently hidden [hermes_project_work/bindings.py:135]
- [x] [Review][Patch] Provider metadata persists without a valid Controller Identity [hermes_project_work/bindings.py:299]
- [x] [Review][Patch] Identity paths and profiles accept invalid or non-canonical values [hermes_project_work/bindings.py:102]
- [x] [Review][Patch] GitHub reference key is ambiguous for delimiter-bearing components [hermes_project_work/bindings.py:112]
- [x] [Review][Patch] JSON inputs can change during an accepted persistence round trip [hermes_project_work/bindings.py:316]
- [x] [Review][Patch] Primary-key collisions retry into an empty conflict diagnostic [hermes_project_work/bindings.py:441]
- [x] [Review][Patch] Focused acceptance suite contradicts profile semantics and cannot inject rollback failure [tests/project_work/test_bindings.py:326]
- [x] [Review][Patch] TEA identity scenarios reuse hidden uniqueness dimensions [tests/project_work/test_bindings.py:111]
- [x] [Review][Patch] TEA transaction, lock, restart, identity, and index tests can pass without proving their claims [tests/project_work/test_bindings.py:576]
- [x] [Review][Patch] Create still commits unrelated caller work before validation [hermes_project_work/bindings.py:438]
- [x] [Review][Patch] Locked initialization still returns an unusable connection [hermes_project_work/bindings.py:134]
- [x] [Review][Patch] Provider identity and metadata shape validation remains incomplete [hermes_project_work/bindings.py:316]
- [x] [Review][Patch] Profile and BMAD path identities remain non-canonical [hermes_project_work/bindings.py:102]
- [x] [Review][Patch] Uniqueness and forced-ID tests still pass through non-target conflicts [tests/project_work/test_bindings.py:215]
- [x] [Review][Patch] TEA rollback, restart, schema, lock, and process tests remain false-positive evidence [tests/project_work/test_bindings.py:674]
- [x] [Review][Patch] Create-side schema initialization still commits caller transactions and bypasses lock retry [hermes_project_work/bindings.py:137]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed or type-losing values [hermes_project_work/bindings.py:328]
- [x] [Review][Patch] Blank BMAD paths and Windows roots still normalize to incorrect identities [hermes_project_work/bindings.py:102]
- [x] [Review][Patch] Primary-key collision handling still retries and its test never reaches the path [hermes_project_work/bindings.py:489]
- [x] [Review][Patch] TEA tests still provide false-positive import, race, rollback, restart, and schema evidence [tests/project_work/test_bindings.py:65]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed or type-losing values [hermes_project_work/bindings.py:344]
- [x] [Review][Patch] Primary-key collisions still retry and raise instead of returning a machine-readable conflict [hermes_project_work/bindings.py:511]
- [x] [Review][Patch] Per-path schema initialization cache is populated but never consulted [hermes_project_work/bindings.py:91]
- [x] [Review][Patch] TEA evidence remains skippable or false-positive across persistence boundaries [tests/project_work/test_bindings.py:65]
- [x] [Review][Patch] Provider identity and JSON fidelity still accept malformed or type-losing inputs [hermes_project_work/bindings.py:372]
- [x] [Review][Patch] Cached schema initialization does not verify or retry the complete schema [hermes_project_work/bindings.py:169]
- [x] [Review][Patch] TEA evidence remains skippable or false-positive across persistence boundaries [tests/project_work/test_bindings.py:65]
- [x] [Review][Patch] New Project Binding package is omitted from distributions [pyproject.toml:356]
- [x] [Review][Patch] Provider identity and JSON contract validation remains lossy and incomplete [hermes_project_work/bindings.py:389]
- [x] [Review][Patch] Cached schema initialization remains incomplete and lacks warm-path retry [hermes_project_work/bindings.py:229]
- [x] [Review][Patch] Green TEA suite still provides false-positive and non-portable persistence evidence [tests/project_work/test_bindings.py:65]
- [x] [Review][Patch] Cached schema initialization still accepts incomplete schemas and does not perform additive repair [hermes_project_work/bindings.py:229]
- [x] [Review][Patch] Provider identity and JSON validation still admits malformed or type-losing values [hermes_project_work/bindings.py:402]
- [x] [Review][Patch] TEA evidence still skips race tests and does not prove rollback/schema relationships [tests/project_work/test_bindings.py:714]
- [x] [Review][Patch] Cached schema repair still accepts incomplete schemas and broken index definitions [hermes_project_work/bindings.py:238]
- [x] [Review][Patch] Provider identity and JSON validation still permits type loss and inconsistent controller identities [hermes_project_work/bindings.py:417]
- [x] [Review][Patch] TEA persistence evidence still misses real rollback/schema/race boundaries [tests/project_work/test_bindings.py:1092]
- [x] [Review][Patch] Profile-scoped listing bypasses profile normalization [hermes_project_work/bindings.py:704]
- [x] [Review][Patch] Cached schema verification and repair still do not prove or restore the complete persistence contract [hermes_project_work/bindings.py:238]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed, type-losing, and contradictory data [hermes_project_work/bindings.py:427]
- [x] [Review][Patch] TEA persistence evidence still misses schema predicate, rollback, and race boundaries [tests/project_work/test_bindings.py:714]
- [x] [Review][Patch] Cached schema verification and repair still do not prove or restore the complete persistence contract [hermes_project_work/bindings.py:245]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed, type-losing, cyclic, and contradictory data [hermes_project_work/bindings.py:442]
- [x] [Review][Patch] TEA persistence evidence still misses schema predicate, rollback, and race boundaries [tests/project_work/test_bindings.py:1132]
- [x] [Review][Patch] Schema verification and cached repair still do not prove or restore the complete persistence contract [hermes_project_work/bindings.py:251]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed, type-losing, and contradictory data [hermes_project_work/bindings.py:384]
- [x] [Review][Patch] TEA persistence evidence still misses schema predicate, rollback, and race boundaries [tests/project_work/test_bindings.py:1153]
- [x] [Review][Patch] Schema verification and cached repair still do not prove or restore the complete persistence contract [hermes_project_work/bindings.py:251]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed, type-losing, and contradictory data [hermes_project_work/bindings.py:384]
- [x] [Review][Patch] TEA persistence evidence still misses schema predicate, rollback, and race boundaries [tests/project_work/test_bindings.py:1153]
- [x] [Review][Patch] Schema verification and cached repair still do not prove or restore the complete persistence contract [hermes_project_work/bindings.py:251]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed, type-losing, and contradictory data [hermes_project_work/bindings.py:384]
- [x] [Review][Patch] TEA persistence evidence still misses schema predicate, rollback, lock, and race boundaries [tests/project_work/test_bindings.py:1153]
- [x] [Review][Patch] Schema verification and repair still do not prove or restore the full persistence contract [hermes_project_work/bindings.py:251]
- [x] [Review][Patch] Provider identity and JSON validation still accepts malformed, type-losing, and contradictory data [hermes_project_work/bindings.py:474]
- [x] [Review][Patch] TEA persistence evidence still misses schema predicate, rollback, lock, path, and race boundaries [tests/project_work/test_bindings.py:1153]
- [x] [Review][Patch] Schema initialization and repair can still return an invalid database or delete persisted Project Bindings [hermes_project_work/bindings.py:205]
- [x] [Review][Patch] Provider identity and JSON validation still accept lossy and contradictory persisted identities [hermes_project_work/bindings.py:528]
- [x] [Review][Patch] The focused TEA suite still contains false-positive and non-portable persistence evidence [tests/project_work/test_bindings.py:1079]
- [x] [Review][Patch] Schema initialization and repair still accept invalid Project Binding schemas and can leave uniqueness/identity constraints unenforced [hermes_project_work/bindings.py:205]
- [x] [Review][Patch] Provider Controller Identity and JSON validation still accept lossy and contradictory persisted identities [hermes_project_work/bindings.py:552]
- [x] [Review][Patch] The focused TEA suite still contains false-positive and non-portable persistence evidence [tests/project_work/test_bindings.py:1878]
- [x] [Review][Patch] Schema initialization and verification still accept invalid Project Binding schemas and can return unusable or under-constrained databases [hermes_project_work/bindings.py:205]
- [x] [Review][Patch] Provider Controller Identity and JSON validation still accept lossy, blank, and contradictory persisted identities [hermes_project_work/bindings.py:553]
- [x] [Review][Patch] The focused TEA suite still contains false-positive and non-portable persistence evidence [tests/project_work/test_bindings.py:1870]
- [x] [Review][Patch] Schema initialization and verification still accept invalid Project Binding schemas and can return unusable or under-constrained databases [hermes_project_work/bindings.py:205]
- [x] [Review][Patch] Provider Controller Identity and JSON validation still accept lossy, blank, and contradictory persisted identities [hermes_project_work/bindings.py:582]
- [x] [Review][Patch] The focused TEA suite still contains false-positive and non-portable persistence evidence [tests/project_work/test_bindings.py:1870]
- [x] [Review][Patch] Cold init path calls _migrate_add_optional_columns twice (once inside _ensure_schema, once explicitly) while warm path calls it once [hermes_project_work/bindings.py:167]
