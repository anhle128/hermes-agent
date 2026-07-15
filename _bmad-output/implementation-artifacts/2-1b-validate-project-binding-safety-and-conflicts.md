# Story 2.1b: Validate Project Binding Safety And Conflicts

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a workflow operator,
I want Hermes to validate Project Binding safety and cross-binding conflicts,
so that automation fails closed for unsafe or ambiguous project context.

## Acceptance Criteria

1. Given a Bound Project Cwd does not exist or is outside allowed workspace roots, when validation runs, then Hermes rejects activation and returns a structured actionable diagnostic without starting workflow actions. [Source: epics.md#Story 2.1b]
2. Given another Project Binding conflicts on profile, cwd, GitHub, BMAD mount, or workflow provider metadata, when validation runs, then Hermes blocks ambiguous automation and returns affected binding references plus conflict category. [Source: epics.md#Story 2.1b]
3. Given a Bound Project Cwd exists but is not a git repository, when validation runs, then Hermes treats it as unsafe and returns a diagnostic identifying the missing `.git` directory as the reason. [Derived from Story 2.1a's own scope-boundary note: "cwd-is-a-git-repo validation — Story 2.1b" — epics.md#Story 2.1a Dev Notes via 2-1a-create-and-persist-project-bindings.md]
4. Given a Project Binding has a BMAD skill directory reference that does not exist on disk, when validation runs, then Hermes reports an invalid BMAD reference diagnostic without raising an exception. [Derived from Implementation Scope: "GitHub and BMAD reference validation" — epics.md#Story 2.1b]
5. Given a Project Binding's stored `github_reference` or `provider_metadata` would fail 2.1a's structural checks (e.g., malformed Controller Identity, non-dict shape), when validation runs, then Hermes returns a structured diagnostic instead of letting `ValueError`/`TypeError` propagate to the caller. [Derived from Implementation Scope: "provider-metadata validation" plus Blocking behavior: "actionable diagnostics" — epics.md#Story 2.1b]
6. Given a fully valid, non-conflicting Project Binding, when validation runs, then Hermes returns `validation_state: "valid"`, `safe: True`, no diagnostics, and an empty conflicts list. [Derived from Integration validation: "fail closed... without enabling automation" (implies the converse: a valid binding is not blocked) — epics.md#Story 2.1b]
7. Given a not-yet-created candidate binding's field values match another existing binding's `bound_project_cwd`, `github_reference_key`, `bmad_skill_dir`, or `(provider_name, provider_binding_name)` within the same profile, when a caller previews conflicts before creating it, then Hermes returns each conflicting dimension's category and the existing binding's id without creating any row. [Derived from Contract needed: "conflict categories" plus AC 2's "affected binding references plus conflict category" — epics.md#Story 2.1b]

## Tasks / Subtasks

- [x] Task 1: Implement the Bound Project Cwd safety check — the allowed-root policy (AC: 1, 3)
  - [x] Add `_check_cwd_safety(cwd: str) -> dict` to `hermes_project_work/bindings.py`, returning `{"valid": bool, "reason": Optional[str]}`.
  - [x] Check in this order, returning on the first failure (a check on a nonexistent path is meaningless, so existence must gate the rest):
    1. `"cwd_does_not_exist"` — `not Path(cwd).exists()`.
    2. `"cwd_is_not_a_directory"` — exists but `not Path(cwd).is_dir()`.
    3. `"cwd_is_filesystem_root"` — `Path(cwd).parent == Path(cwd)` (a path is its own parent only at a filesystem root; this check is portable across POSIX `/` and Windows drive roots like `C:\`, unlike a hardcoded `"/"` string compare).
    4. `"cwd_is_within_hermes_home"` — the resolved `cwd` equals or is nested under `Path(get_hermes_home()).resolve()`. Binding Hermes's own state/config directory as an automation "project" is a self-modifying-automation hazard, not a hypothetical: BMAD/provider workflow actions running there could corrupt Hermes's own profile data.
    5. `"cwd_is_not_a_git_repository"` — `not (Path(cwd) / ".git").is_dir()`. This is the existing codebase convention for "is a git repo" — see `hermes_cli/config.py:444`, `hermes_cli/plugins_cmd.py:648`, `hermes_cli/web_server.py:1408` (`(root / ".git").is_dir()` / `(target / ".git").exists()`); do not invent a new detection method (e.g. shelling out to `git rev-parse`).
  - [x] This function is the concrete local definition of the "allowed-root policy" that epics.md lists as a needed contract with no parent artifact — this story is the source of that policy, not a consumer of one. Document the rationale above as a code comment (non-obvious business rule).
  - [x] `_check_cwd_safety` assumes its input is already an absolute, normalized path (i.e. the value already stored via `_normalize_path` at creation time, `bindings.py:103-132`) — do not re-normalize inside this function.

- [x] Task 2: Implement the BMAD skill directory reference safety check (AC: 4)
  - [x] Add `_check_bmad_reference_safety(bmad_skill_dir: Optional[str]) -> Optional[dict]`.
  - [x] Return `None` when `bmad_skill_dir` is `None` — nothing to validate, matching `ProjectBinding.bmad_skill_dir`'s Optional shape (`bindings.py:491`).
  - [x] Otherwise return `{"valid": bool, "reason": Optional[str]}` with reasons `"bmad_skill_dir_does_not_exist"` / `"bmad_skill_dir_is_not_a_directory"`.
  - [x] Do NOT touch `skills.external_dirs`, attempt a mount, or reload any profile skill index — mounting, reload, and the "wrong-project mount" diagnostic belong entirely to Story 2.2. This check only proves the referenced path currently exists on disk.

- [x] Task 3: Implement non-raising re-validation wrappers for GitHub reference and provider metadata (AC: 5)
  - [x] Add `_check_github_reference_safety(github_reference: Optional[dict]) -> dict` that calls the existing `_validate_github_reference()` (`bindings.py:576-600`) inside `try/except (TypeError, ValueError) as exc`, converting any raised exception into `{"valid": False, "reason": str(exc)}`. Returns `{"valid": True, "reason": None}` when the reference is `None` or passes.
  - [x] Add `_check_provider_metadata_safety(provider_name, provider_binding_name, provider_metadata) -> dict` that calls the existing `_validate_provider_identity()` (`bindings.py:675-733`) the same way — catch, don't raise.
  - [x] Add a small validation-only row loader or equivalent raw-row path for `validate_binding()`: query `project_bindings` directly, parse `github_reference` and `provider_metadata` independently, and convert malformed JSON, non-dict parsed JSON, or provider identity shape failures into the corresponding `*_check: {"valid": False, "reason": ...}` result. Do not let `_binding_from_row()`/`get_binding()` raise before diagnostics can be assembled.
  - [x] Rationale (add as a code comment): `create_binding()` intentionally *raises* on these inputs — fail-fast, pre-mutation, correct for the create path (`bindings.py:837-843`). `validate_binding()` re-checks an already-persisted row and must always return a structured result, even for malformed stored data, per this story's "structured actionable diagnostic" requirement (AC 1) — an unhandled exception is not a diagnostic.
  - [x] Do not duplicate `_validate_github_reference`'s or `_validate_provider_identity`'s logic — call them, don't reimplement them.

- [x] Task 4: Implement conflict detection — pre-flight preview and existing-binding re-scan (AC: 2, 6, 7)
  - [x] Add a module-level `_CONFLICT_CATEGORY_BY_DIMENSION` dict mapping the existing `_check_uniqueness_dimensions()` (`bindings.py:760-808`) violation keys to category strings: `"bound_project_cwd" -> "cwd_conflict"`, `"github_reference_key" -> "github_reference_conflict"`, `"bmad_skill_dir" -> "bmad_mount_conflict"`, `"provider_identity" -> "provider_identity_conflict"`.
  - [x] Extend `_check_uniqueness_dimensions()` with an optional keyword-only `exclude_binding_id: Optional[str] = None`; when provided, each dimension query must exclude that row in SQL. Existing create-path and preview calls pass nothing; `validate_binding()` passes the binding's own id. Do not rely on post-filtering a self-hit after the query, because a damaged DB without the expected unique guarantees could otherwise hide a sibling collision behind the current row.
  - [x] Add `preview_binding_conflicts(conn, *, profile=None, bound_project_cwd, github_reference=None, bmad_skill_dir=None, provider_name=None, provider_binding_name=None) -> list[dict]`. Normalize inputs exactly like `create_binding()` does — reuse `_resolve_profile`, `_normalize_path`, `_github_reference_key`, `_validate_provider_identity` (`bindings.py:837-849`); do not duplicate that normalization. Call `_check_uniqueness_dimensions()` and map the returned `{dimension: existing_id}` through `_CONFLICT_CATEGORY_BY_DIMENSION` into `[{"category": ..., "conflicting_binding_id": ...}, ...]`. Read-only — never inserts a row.
  - [x] **Critical invariant, read before writing tests:** all four uniqueness dimensions are enforced by hard partial unique indexes (`SCHEMA_SQL`, `bindings.py:71-84`). Two *persisted* bindings for the same profile can never simultaneously collide on any of these dimensions — that is true regardless of which code path inserted or updated the row, because SQLite enforces unique indexes on every `INSERT` and `UPDATE`. `preview_binding_conflicts()`, called before a row exists, is the *only* path where a non-empty conflict list is reachable. Do not attempt to force two colliding persisted rows into the table for a test — the second write will always raise `IntegrityError` by design (this is exactly the guarantee 2.1a's uniqueness enforcement provides). See Task 6 for the corresponding invariant test.

- [x] Task 5: Implement `validate_binding(conn, binding_id) -> dict` — the unified entrypoint (AC: 1, 2, 3, 4, 5, 6)
  - [x] Load the row by id; raise `ValueError` only when `binding_id` does not resolve to any row (a caller/programmer error, not a validation outcome). For well-formed rows, using `get_binding()` (`bindings.py:921-929`) is fine. For malformed stored JSON/non-dict JSON in `github_reference` or `provider_metadata`, do not call `get_binding()` in a way that lets `_binding_from_row()` raise before AC5 diagnostics are returned.
  - [x] Run `_check_cwd_safety`, `_check_bmad_reference_safety`, `_check_github_reference_safety`, `_check_provider_metadata_safety` against the binding's current stored fields (re-checking live filesystem state, not just what was true at creation time — the whole point of a re-validation entrypoint is that a directory can be deleted or a `.git` folder removed after the binding was created). If a JSON field cannot be parsed or parses to a non-dict, mark only that reference check invalid and continue assembling the full validation result.
  - [x] Run the conflict scan using the same dimension-checking logic as `preview_binding_conflicts`, scoped to the binding's own profile and **excluding its own id** from any match (a binding must never be reported as conflicting with itself). Per Task 4's invariant, expect this to always return `[]` for any binding created through `create_binding()` — implement it anyway, as the defense-in-depth path Story 2.1c's future update flow will rely on.
  - [x] Assemble `diagnostics: list[dict]`, one entry per failed check or conflict, each shaped `{"category": str, "message": str, "next_action_owner": "configuration", "recovery_option": str}`. Reuse the **exact** enum value strings already defined in `_bmad-output/planning-artifacts/contracts/workflow-commander/schemas/operational-diagnostic.schema.json`: `nextActionOwner` = `"configuration"` (schema lines 75-85) for every diagnostic this story produces (matches epics.md's Diagnostic Family Matrix "configuration" row: "Project Binding validation, Bound Project Cwd checks, BMAD mount checks, provider binding diagnostics | configuration action | repair binding, cwd, BMAD mount, or provider metadata" — epics.md lines 662-663). Use `recovery_option = "repair_project_binding"` (schema line 91) for cwd/bmad/github/provider-metadata invalid diagnostics, and `recovery_option = "update_project_binding"` (schema line 98) for conflict diagnostics — both strings already exist in that schema's `recoveryOptions` enum; do not invent new ones.
  - [x] `category` on each diagnostic is this story's own fine-grained local vocabulary (`invalid_cwd`, `invalid_bmad_reference`, `invalid_github_reference`, `invalid_provider_metadata`, `cwd_conflict`, `github_reference_conflict`, `bmad_mount_conflict`, `provider_identity_conflict`) — deliberately more granular than the operational-diagnostic schema's own coarse `category` enum (`configuration`, `user_decision`, ...), which is Story 5.3a's cross-story taxonomy. Do not conflate the two; a future 5.3a persistence pass can bucket all of this story's categories under that schema's `"configuration"` value.
  - [x] Compute a top-level `validation_state` string using this precedence when more than one thing is wrong (first match wins): `"invalid_cwd"` > `"invalid_bmad_reference"` > `"invalid_github_reference"` > `"invalid_provider_metadata"` > `"conflicting"` > `"valid"`. This is the local value space ("validation-state transitions" per Implementation Scope) that this story establishes; it is computed fresh on every call, not persisted. **Story 2.1c** is the one that will store the latest computed value into a durable `validation_state` column and manage transitions over time (e.g. re-validate on a schedule, flip `enabled` accordingly) — this story only defines what the possible values are and how to compute one.
  - [x] Return `{"binding_id": ..., "safe": bool, "validation_state": str, "cwd_check": {...}, "bmad_reference_check": {...} | None, "github_reference_check": {...}, "provider_metadata_check": {...}, "conflicts": [...], "diagnostics": [...]}`. `safe` is `True` iff every check's `valid` is `True` (or `None` for the optional BMAD check) and `conflicts` is empty (equivalently, `validation_state == "valid"`).
  - [x] This function requires **no new database columns** — it is a pure, on-demand computation over already-persisted fields plus current filesystem/sibling-row state. Do not add `enabled` or `validation_state` columns, and do not call `_migrate_add_optional_columns()` with new column DDL — that seam is explicitly reserved for **Story 2.1c**, which owns the persisted `enabled`/`validation_state`/audit fields and the lifecycle commands (update/disable/repair/re-enable) that will call `validate_binding()` as their safety gate.

- [x] Task 6: Tests — cwd safety, BMAD safety, reference re-validation, conflict preview, end-to-end `validate_binding` (AC: 1-7)
  - [x] Add new test classes to `tests/project_work/test_bindings.py` (do not create a new test file — this module already holds all Project Binding test coverage).
  - [x] `TestCwdSafetyValidation`: cwd does not exist; cwd exists but is a file, not a directory; cwd is a filesystem root (unit-test `_check_cwd_safety` directly with a constructed root-like path — `tmp_path` fixtures cannot naturally produce a real root); cwd resolves inside `get_hermes_home()` (monkeypatch `hermes_project_work.bindings.get_hermes_home` to return `tmp_path`, then check a nested path); cwd exists and is a directory but has no `.git` subdirectory; happy path — real `tmp_path` directory with a `.git` subdirectory created via `(tmp_path / ".git").mkdir()`.
  - [x] `TestBmadReferenceSafety`: `None` input returns `None`; missing directory; path is a file, not a directory; valid existing directory.
  - [x] `TestGithubAndProviderMetadataSafety`: valid inputs return `valid: True`; feed each wrapper an input shape that would raise from the underlying `_validate_github_reference`/`_validate_provider_identity` (e.g. non-dict `github_reference`, one-sided provider identity) and assert no exception escapes — a `reason` string is returned instead.
  - [x] `TestPreviewBindingConflicts`: one test per dimension (`bound_project_cwd`, `github_reference_key`, `bmad_skill_dir`, `provider_identity`) — create a real binding via `create_binding()`, then call `preview_binding_conflicts()` with candidate values matching exactly one dimension and assert the correct category plus the existing binding's id are returned; one test proving a genuinely non-conflicting candidate returns `[]`.
  - [x] `TestValidateBinding` (end-to-end, real SQLite, real filesystem via `tmp_path` — no mocks, per this project's testing rules):
    - Fully valid binding (real git-backed `tmp_path` directory) → `safe: True`, empty `diagnostics`, empty `conflicts`.
    - Binding created with a `bound_project_cwd` that never existed on disk (2.1a's `create_binding` does not check existence, so this is constructible) → `safe: False`, a `diagnostics` entry with `category: "invalid_cwd"`.
    - Binding with an existing, non-git `bound_project_cwd` → flagged with the `cwd_is_not_a_git_repository` reason.
    - Binding with a `bmad_skill_dir` pointing at a nonexistent path → `category: "invalid_bmad_reference"` diagnostic.
    - Binding whose persisted `github_reference` column is malformed JSON or parses to a non-dict (created via raw SQL update after a valid `create_binding()` call, because the create path correctly rejects this) → `safe: False`, no exception escapes, `validation_state: "invalid_github_reference"`, and a diagnostic with `category: "invalid_github_reference"`.
    - Binding whose persisted `provider_metadata` or Controller Identity columns are malformed (non-dict JSON, invalid JSON, one-sided `provider_name`/`provider_binding_name`, or metadata present without a complete identity, injected via raw SQL update) → `safe: False`, no exception escapes, `validation_state: "invalid_provider_metadata"`, and a diagnostic with `category: "invalid_provider_metadata"`.
    - Unknown `binding_id` → `validate_binding()` raises `ValueError`.
    - **Invariant test:** any binding created through `create_binding()` always has `conflicts == []` when re-validated — proving the unique-index guarantee described in Task 4 holds for the existing-binding re-scan path.
  - [x] Follow the `tmp_path`-based, real-connection, no-mock fixture convention already used throughout this test file (and required by this project's Testing Rules for code touching file/persistence I/O).

### Review Findings

- [x] [Review][Patch] `validate_binding()` raises on invalid UTF-8 JSON bytes [hermes_project_work/bindings.py:1140]
- [x] [Review][Patch] `preview_binding_conflicts()` accepts a blank profile unlike `create_binding()` [hermes_project_work/bindings.py:1087]
- [x] [Review][Patch] `git diff --check` fails on trailing whitespace [_bmad-output/test-artifacts/test-design-epic-2.1b.md:34]
- [x] [Review][Patch] `git diff --check` still fails on trailing whitespace [_bmad-output/test-artifacts/test-design-epic-2.1b.md:35]
- [x] [Review][Patch] Provider metadata invalid UTF-8 regression coverage is missing [tests/project_work/test_bindings.py:3673]
- [ ] [Review][Patch] `validate_binding()` suppresses conflict diagnostics when stored JSON is malformed [hermes_project_work/bindings.py:1218]

## Dev Notes

### Scope boundary — read this before writing any code

This story is deliberately narrow, matching 2.1a's own discipline. Per epics.md, Story 2.1b's Implementation Scope is exactly: "Hermes allowed-root cwd validation, GitHub and BMAD reference validation, provider-metadata validation, conflict detection, validation-state transitions, and actionable diagnostics." The following are explicitly OUT of scope here even though they sound adjacent:

- **Persisted `enabled` / `validation_state` columns, and lifecycle commands** (update, disable, repair, re-enable, audit history) — **Story 2.1c**. 2.1a's `_migrate_add_optional_columns()` stub (`bindings.py:469-475`) was reserved for "2.1b/2.1c" — this story does NOT use that seam. Read `2-1a-create-and-persist-project-bindings.md`'s own Dev Notes scope-boundary list: it assigns `enabled`/`validation_state`/audit history to **2.1c specifically**, not this story. `validate_binding()` here is a pure computed function over existing columns; nothing is persisted.
- **Actually mounting BMAD skills into `skills.external_dirs`, reloading the profile skill index, or the "wrong-project mount" diagnostic** — **Story 2.2**. This story only checks that the referenced directory exists on disk.
- **Wiring cwd validation into BMAD/provider workflow action execution** (the actual cwd guard that blocks a running workflow) — **Story 2.3**. This story only builds the validation function; nothing yet calls it before starting a workflow action.
- **Archon provider binding registration, liveness, or status (`missing`/`valid`/`stale`/`disabled`/`rotated`/`conflicting`)** — **Story 3.2**. This story validates the *shape* of what 2.1a already stored locally in `provider_metadata`; it never talks to Archon.
- **Durable, schema-versioned `OperationalDiagnostic` records with `diagnosticId`/`severity`/`redactionApplied`/persistence** — **Story 5.3a**. This story returns diagnostics as plain dicts from a function call; it does not persist a diagnostic history. It does, however, reuse 5.3a's already-shipped `nextActionOwner`/`recoveryOptions` vocabulary strings so that future persistence is a straight mapping, not a rename.

Only build: cwd safety check (existence, directory, filesystem-root/Hermes-home denylist, git-repo), BMAD reference existence check, non-raising GitHub/provider-metadata re-validation, conflict-category mapping for both pre-flight preview and existing-binding re-scan, and the unified `validate_binding()`/`preview_binding_conflicts()` functions.

**On AC 1's wording "rejects activation":** there is no `activate_binding()` command in this story (or anywhere yet) — "activation" describes what a *future* caller (Story 2.3's cwd guard, Story 2.1c's enable/re-enable lifecycle) must refuse to do when `validate_binding()` reports unsafe. This story's deliverable is the safety-check function those future callers will gate on, not a new command surface. Do not add an `activate_binding()`/`enable_binding()` function here — that is scope creep into Story 2.1c.

### Why `validate_binding()` needs zero new schema

`create_binding()` (2.1a) already persists every field this story needs to inspect: `bound_project_cwd`, `bmad_skill_dir`, `github_reference`, `provider_name`/`provider_binding_name`/`provider_metadata`. This story's whole job is to *re-examine* those already-stored values against **current** filesystem state (a directory can be deleted after the binding was created — that is precisely why a stateless, on-demand recheck function is useful and cannot simply be "done once at create time") and against current sibling rows. No new column is needed to represent a validation *result*, because the result is not durable state — it is recomputed every call. Story 2.1c is the one that will persist a `validation_state` column driven by calling this story's `validate_binding()`.

### The allowed-root policy is defined by this story, not inherited

Epics.md lists "allowed-root policy" under this story's "Contract needed" line with no corresponding schema file under `contracts/workflow-commander/` (that package only covers Archon-facing command/event/binding/delivery contracts — see its README; there is no Project-Binding-specific schema there because Project Binding is entirely Hermes-internal). This story is the place that policy gets defined. The concrete rule this story establishes: a Bound Project Cwd must (1) exist, (2) be a directory, (3) not be a filesystem root, (4) not be `get_hermes_home()` itself or nested inside it, and (5) contain a `.git` directory. Rules 3-4 are a minimal, justified denylist (root is too broad/destructive as an automation target; Hermes's own home directory is a self-modifying-automation hazard) rather than a broad configurable allow-list — there is no PRD requirement for admin-configurable roots, and this codebase's conventions favor a narrow, justified default over speculative configuration surface. Rule 5 comes directly from 2.1a's own Dev Notes, which explicitly deferred "cwd-is-a-git-repo validation" to this story by name.

### The conflict-detection duality — read this before designing tests

`_check_uniqueness_dimensions()` (`bindings.py:760-808`, already built by 2.1a) is called today only *inside* `create_binding()`'s write transaction. Because every one of its four dimensions is backed by a hard `CREATE UNIQUE INDEX` (`bindings.py:71-84`), **no two persisted rows for the same profile can ever collide** on any of those dimensions — full stop, regardless of which code path wrote them, because SQLite enforces unique indexes on both `INSERT` and `UPDATE`. This means:

- `preview_binding_conflicts()` (new, pre-flight, no row created yet) is where a non-empty conflict list is actually reachable and worth testing thoroughly (Task 6, `TestPreviewBindingConflicts`).
- The conflict scan inside `validate_binding()` (re-validating an *existing* row against its siblings, self excluded) will always return `[]` today. That is not dead code — it is the safety net Story 2.1c's future `update_binding()` will lean on if its own write path does not re-run the same pre-check `create_binding()` does before every mutation. Implement it, and add the invariant test proving it stays empty (Task 6) — do not skip it because it "can't fail yet."

### Non-raising vs. raising validation — know which one you're calling

2.1a's `_validate_github_reference()` and `_validate_provider_identity()` (`bindings.py:576-600`, `675-733`) are *fail-fast* validators built for `create_binding()`'s pre-mutation contract — they raise `TypeError`/`ValueError` on bad input, which is correct there (reject before writing). This story wraps both in non-raising checkers (`_check_github_reference_safety`, `_check_provider_metadata_safety`) because `validate_binding()`'s whole contract is "return a structured diagnostic, never crash the caller" (AC 1, AC 5) — an already-persisted row's stored JSON could in principle be malformed from a future write path that doesn't reuse 2.1a's validators, and this story's re-validation entrypoint must degrade to a diagnostic, not an exception, in that case.

Important: `get_binding()` currently calls `_binding_from_row()`, which parses JSON and intentionally raises `ValueError` when `github_reference` or `provider_metadata` parses to a non-dict (`bindings.py:511-529`). That fail-fast read contract is correct for normal callers, but `validate_binding()` must not inherit it blindly. Use a raw-row validation path or catch-and-convert around JSON parsing so AC5 is tested at the end-to-end `validate_binding()` boundary, not only at the private wrapper boundary.

### Reuse map (do not reimplement any of these)

- `get_binding()` (`bindings.py:921-929`) — load well-formed binding rows for `validate_binding()`. Do not rely on it for AC5 malformed stored JSON cases, because `_binding_from_row()` raises before validation diagnostics can be returned.
- `_normalize_path()` (`bindings.py:103-132`) — already-normalized form is what's stored; `_check_cwd_safety` assumes it, `preview_binding_conflicts` must call it on candidate input the same way `create_binding` does.
- `_github_reference_key()` (`bindings.py:135-141`) — for `preview_binding_conflicts`'s github dimension.
- `_validate_github_reference()`, `_validate_provider_identity()` (`bindings.py:576-600`, `675-733`) — wrap, don't reimplement.
- `_check_uniqueness_dimensions()` (`bindings.py:760-808`) — the shared engine for both `preview_binding_conflicts` and `validate_binding`'s conflict scan.
- `_resolve_profile()` (`bindings.py:545-559`) — for `preview_binding_conflicts`'s `profile=None` default.
- `.git` directory existence as the codebase's established "is a git repo" check — `hermes_cli/config.py:444`, `hermes_cli/plugins_cmd.py:648`, `hermes_cli/web_server.py:1408`. Do not shell out to `git rev-parse --git-dir` or add a new dependency for this.
- `operational-diagnostic.schema.json`'s `nextActionOwner`/`recoveryOptions` enum value strings (`"configuration"`, `"repair_project_binding"`, `"update_project_binding"`) — reuse the exact strings for forward compatibility with Story 5.3a's future diagnostic persistence.

### Architecture alignment

- Matches AD-5 (`architecture.md`): Hermes owns cross-system safety/conflict detection; this story is the Project-Binding-local slice of that authority (full cross-system reconciliation is Epic 5).
- Matches AD-6: `hermes-agent` owns Project Binding validation entirely in-process; no Archon call is made.
- Matches AD-8: no new runtime infrastructure, no new dependency — pure Python + `pathlib` + the existing SQLite connection.
- Satisfies NFR-7 groundwork ("Workflow actions cannot run outside the selected Bound Project Cwd") by providing the safety check Story 2.3 will call before starting any action — this story does not wire that call itself.
- Satisfies NFR-14 ("recovery options instead of raw stack traces alone") directly: `validate_binding()`'s diagnostics always carry a `recovery_option`, and never raise for content-shape problems.

### Testing standards

- Python tests via `uv run pytest` (or `scripts/run_tests.sh` for the full isolated-subprocess run). All new tests go in `tests/project_work/test_bindings.py` (existing file — do not fragment coverage into a new file).
- Use real SQLite connections against `tmp_path` and real filesystem directories for cwd/BMAD-dir checks — no mocks, per this project's Testing Rules for code touching file/persistence I/O (`project-context.md`).
- `_check_cwd_safety`'s Hermes-home-denylist check needs `get_hermes_home` to be monkeypatchable per-test (it already is, since `bindings.py` imports it as a module-level name — patch `hermes_project_work.bindings.get_hermes_home`, matching how other tests in this file already patch module-level collaborators).

### Project Structure Notes

- No new files. Only `hermes_project_work/bindings.py` (add functions) and `tests/project_work/test_bindings.py` (add test classes) are touched — both already exist from Story 2.1a.
- No wiring into `cli.py`, `toolsets.py`, or any command surface yet — that comes with later stories (2.3, 2.4) that actually need to call `validate_binding()` before starting workflow actions.
- No conflicts with any other in-flight story: 2.1c, 2.2, 2.3, and 3.2 all depend on this story but have not yet touched `hermes_project_work/bindings.py`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1b: Validate Project Binding Safety And Conflicts]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 2: Project-Bound Planning And Work Backlog (Ownership Boundary, Diagnostic Family Matrix under Story 5.3a)]
- [Source: _bmad-output/planning-artifacts/prd.md#FR-1: Create And View Project Bindings, NFR-7, NFR-14]
- [Source: _bmad-output/planning-artifacts/architecture.md#AD-5, AD-6, AD-8]
- [Source: _bmad-output/planning-artifacts/contracts/workflow-commander/schemas/operational-diagnostic.schema.json (nextActionOwner, recoveryOptions enums)]
- [Source: _bmad-output/planning-artifacts/contracts/workflow-commander/README.md (confirms no Project-Binding-specific schema exists in the shared package — this story defines its own local validation result shape)]
- [Source: _bmad-output/implementation-artifacts/2-1a-create-and-persist-project-bindings.md — Dev Notes scope-boundary list assigning cwd-exists/allowed-root/git-repo validation, conflict categories, and diagnostic vocabulary to this story, and enabled/validation_state/audit history to Story 2.1c]
- [Source: hermes_project_work/bindings.py — `_normalize_path`, `_github_reference_key`, `_validate_github_reference`, `_validate_provider_identity`, `_check_uniqueness_dimensions`, `create_binding`, `get_binding`, `_migrate_add_optional_columns`, `SCHEMA_SQL` unique indexes]
- [Source: hermes_cli/config.py:444 — `(root / ".git").is_dir()` git-repo detection convention]
- [Source: hermes_cli/plugins_cmd.py:648, hermes_cli/web_server.py:1408 — same `.git` existence convention reused elsewhere]
- [Source: hermes_constants.py#get_hermes_home — profile home resolution used for the Hermes-home denylist check]
- [Source: tests/project_work/test_bindings.py — existing `tmp_path`/real-SQLite fixture conventions to extend]
- [Source: _bmad-output/project-context.md — testing rules requiring real imports/temp paths over mocks for file/persistence I/O]

## Dev Agent Record

### Agent Model Used

Qoder (Claude)

### Debug Log References

All 209 tests in `tests/project_work/test_bindings.py` pass (75 new Story 2.1b tests + 134 existing Story 2.1a tests). Fix pass 1 added 3 tests for the review findings. Fix pass 2 added 1 test for provider_metadata UTF-8 coverage.

### Completion Notes List

- Implemented `_check_cwd_safety()` with the allowed-root policy: existence, directory, filesystem-root deny, Hermes-home deny, git-repo check.
- Implemented `_check_bmad_reference_safety()` — existence-only check, no mounting.
- Implemented `_check_github_reference_safety()` and `_check_provider_metadata_safety()` as non-raising wrappers around existing validators.
- Added `_CONFLICT_CATEGORY_BY_DIMENSION` mapping and `exclude_binding_id` parameter to `_check_uniqueness_dimensions()`.
- Implemented `preview_binding_conflicts()` — read-only pre-flight conflict check.
- Implemented `validate_binding()` — unified re-validation entrypoint with raw-row JSON parsing to handle malformed stored data without exceptions.
- No new database columns added (reserved for Story 2.1c).
- No CLI/toolset wiring added (reserved for Stories 2.3/2.4).

### File List

- `hermes_project_work/bindings.py` — added validation functions, conflict detection, and public entrypoints
- `tests/project_work/test_bindings.py` — 72 new tests (pre-existing red-phase scaffolds, now passing)
