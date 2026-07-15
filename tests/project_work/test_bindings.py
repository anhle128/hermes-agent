"""Red-phase acceptance scaffolds for Story 2.1a — Project Binding persistence.

TDD RED PHASE: `hermes_project_work/bindings.py` does not exist yet (Story 2.1a
Task 1). Every test class below is decorated with ``requires_bindings_module``
(a shared ``skipif(pb is None, ...)`` mark) until that module exists; each
test's docstring/body encodes the exact behavior Tasks 1-4 must implement to
make it pass. Activate this suite by implementing
hermes_project_work/bindings.py per the story tasks — the skip flips
automatically once the import succeeds. The one exception is the standalone
Workflow Commander contract-validator test at the bottom of this file, which
targets an already-shipped fixture package and is intentionally left
undecorated so it runs (and passes) now.

Assumed public contract (undocumented specifics the story leaves to the
implementer; adjust these tests if dev-story lands a different shape):

- ``connect(db_path=None) -> sqlite3.Connection`` — mirrors
  ``hermes_cli.projects_db.connect``.
- ``connect_closing(db_path=None)`` — context manager, mirrors the sibling.
- ``project_bindings_db_path() -> Path`` — ``get_hermes_home() / "project_bindings.db"``.
- ``create_binding(conn, *, profile, display_name, bound_project_cwd,
  github_reference=None, bmad_skill_dir=None, provider_name=None,
  provider_binding_name=None, provider_metadata=None) -> dict`` returns
  ``{"conflict": False, "id": "pb_..."}`` on success or
  ``{"conflict": True, "violations": {<dimension>: <existing_id>, ...}}``
  on any uniqueness collision (Task 2, subtask 3's own wording).
- ``get_binding(conn, binding_id) -> ProjectBinding | None``.
- ``list_bindings_for_profile(conn, profile) -> list[ProjectBinding]``.
- ``ProjectBinding`` dataclass has ``.to_dict()`` mirroring
  ``hermes_cli.projects_db.Project.to_dict()``, with fields: id, profile,
  display_name, bound_project_cwd, github_reference (dict|None),
  bmad_skill_dir (str|None), provider_name (str|None),
  provider_binding_name (str|None), provider_metadata (dict|None),
  created_at (int).
- ``github_reference`` input shape is assumed to be ``{"owner": str, "repo":
  str}`` (R-003 is an open product decision per the test-design doc; update
  the fixtures below if the real contract differs).
- Required-field blank/None rejection (R-001) is assumed to raise
  ``ValueError`` before normalization/SQL, mirroring
  ``hermes_cli.projects_db.create_project``'s ``if not name: raise
  ValueError(...)`` precedent — the story does not pin an exact exception
  type, so this is a documented assumption, not a confirmed contract.

Traceability: each test/parametrize case is tagged with its
``_bmad-output/test-artifacts/test-design-epic-2.1a.md`` scenario ID in a
comment or docstring for the mandatory ATDD mapping.

Story 2.1b (validate Project Binding safety and conflicts) scaffolds live
further down in this same file, in the section headed "Story 2.1b:
Validate Project Binding Safety And Conflicts" — see that section's own
docstring for its red-phase status and
``_bmad-output/test-artifacts/test-design-epic-2.1b.md`` traceability.
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

try:
    from hermes_project_work import bindings as pb
except ModuleNotFoundError as exc:
    if "hermes_project_work" not in str(exc):
        raise
    # Expected until Task 1 lands: hermes_project_work package doesn't exist yet
    pb = None

# Applied per-class (not as a file-wide `pytestmark`) so the standalone
# contract-validator test at the bottom of this file — which targets the
# already-shipped Workflow Commander fixture package, not
# hermes_project_work — is never skipped by this guard.
requires_bindings_module = pytest.mark.skipif(
    pb is None,
    reason=(
        "hermes_project_work.bindings does not exist yet (Story 2.1a, Task 1: "
        "create hermes_project_work/__init__.py and bindings.py with SCHEMA_SQL, "
        "connect()/connect_closing(), create_binding(), get_binding(), "
        "list_bindings_for_profile()). Activates automatically once the module "
        "imports cleanly; see this file's module docstring for the assumed "
        "public contract these tests exercise."
    ),
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "_bmad-output/planning-artifacts/contracts/workflow-commander"
STATUS_VALID_FIXTURE = CONTRACTS_DIR / "examples/providers/archon/bindings/status-valid.json"
VALIDATE_CONTRACTS_SCRIPT = CONTRACTS_DIR / "validate_contracts.py"


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path) -> Path:
    return tmp_path / "project_bindings.db"


@pytest.fixture
def conn(db_path):
    c = pb.connect(db_path=db_path)
    try:
        yield c
    finally:
        c.close()


def valid_kwargs(**overrides: Any) -> dict:
    """A complete, valid set of create_binding() kwargs. Override per test."""
    base = dict(
        profile="default",
        display_name="Hermes Agent",
        bound_project_cwd="/tmp/hermes-agent",
        github_reference={"owner": "NousResearch", "repo": "hermes-agent"},
        bmad_skill_dir="/tmp/hermes-agent/_bmad",
        provider_name="archon",
        provider_binding_name="workflow-engine-primary",
        provider_metadata={"bindingId": "wpb_archon_workflow_engine_primary"},
    )
    base.update(overrides)
    return base


def load_status_valid_fixture() -> dict:
    return json.loads(STATUS_VALID_FIXTURE.read_text(encoding="utf-8"))


def get_row(conn: sqlite3.Connection, binding_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT * FROM project_bindings WHERE id = ?", (binding_id,)
    ).fetchone()
    assert row is not None, f"no persisted row for {binding_id}"
    return row


def row_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM project_bindings").fetchone()[0]


# =============================================================================
# P0 — Blocking Contract/Data Cases
# =============================================================================


@requires_bindings_module
class TestP0BlockingCases:
    def test_reject_blank_cwd_before_normalization_zero_mutation(self, conn):
        """2.1A-INT-007 (P0, R-001): blank cwd must not silently normalize to
        the process cwd. Reject before normalization/SQL; zero rows written."""
        with pytest.raises(ValueError):
            pb.create_binding(conn, **valid_kwargs(bound_project_cwd="   "))
        assert row_count(conn) == 0

    @pytest.mark.parametrize(
        "reference_a,reference_b",
        [
            (
                {"owner": "NousResearch", "repo": "hermes-agent"},
                {"owner": "nousresearch", "repo": "HERMES-AGENT"},
            ),
            (
                {"owner": "Acme", "repo": "Widgets"},
                {"repo": "widgets", "owner": "acme"},
            ),
        ],
        ids=["case-variant", "reordered-keys"],
    )
    def test_semantically_equal_github_references_collide(
        self, conn, reference_a, reference_b
    ):
        """2.1A-INT-013 (P0, AC2/R-003): reordered/case-varied owner+repo must
        canonicalize to the same key and collide, proving the uniqueness check
        never relies on JSON text equality."""
        first = pb.create_binding(
            conn,
            **valid_kwargs(bound_project_cwd="/tmp/a", github_reference=reference_a),
        )
        assert first["conflict"] is False

        second = pb.create_binding(
            conn,
            **valid_kwargs(bound_project_cwd="/tmp/b", github_reference=reference_b),
        )
        assert second["conflict"] is True
        assert second["violations"]["github_reference_key"] == first["id"]
        assert row_count(conn) == 1

    @pytest.mark.parametrize(
        "bad_provider_fields",
        [
            dict(provider_name="archon", provider_binding_name=None),
            dict(provider_name=None, provider_binding_name="workflow-engine-primary"),
            dict(provider_name="", provider_binding_name="workflow-engine-primary"),
            dict(provider_name="archon", provider_binding_name="   "),
            dict(provider_name="   ", provider_binding_name="workflow-engine-primary"),
            dict(provider_name="archon", provider_binding_name=""),
        ],
        ids=[
            "missing-binding-name",
            "missing-provider-name",
            "blank-provider-name",
            "blank-binding-name",
            "whitespace-provider-name",
            "empty-string-binding-name",
        ],
    )
    def test_reject_partial_provider_identity_zero_mutation(
        self, conn, bad_provider_fields
    ):
        """2.1A-INT-017 (P0, R-004/R-010): the generic provider/name Controller
        Identity tuple must be complete or entirely absent — never partial."""
        with pytest.raises(ValueError):
            pb.create_binding(conn, **valid_kwargs(**bad_provider_fields))
        assert row_count(conn) == 0

    def test_each_uniqueness_dimension_reports_independently(self, conn):
        """2.1A-INT-019 (P0, AC2/R-002/R-005): each of the four uniqueness
        dimensions independently reports its own violated dimension and the
        colliding row's id, with exactly one persisted row and no escaped
        sqlite3.IntegrityError.  Each test case overrides ALL non-target
        dimensions to be distinct, preventing non-target conflicts."""
        original = pb.create_binding(conn, **valid_kwargs())
        assert original["conflict"] is False
        original_id = original["id"]

        dimension_overrides = {
            "bound_project_cwd": dict(
                bound_project_cwd="/tmp/hermes-agent",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
            "github_reference_key": dict(
                bound_project_cwd="/tmp/other-a",
                github_reference={"owner": "NousResearch", "repo": "hermes-agent"},
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
            "bmad_skill_dir": dict(
                bound_project_cwd="/tmp/other-b",
                github_reference=None,
                bmad_skill_dir="/tmp/hermes-agent/_bmad",
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
            "provider_identity": dict(
                bound_project_cwd="/tmp/other-c",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name="archon",
                provider_binding_name="workflow-engine-primary",
            ),
        }
        for dimension, overrides in dimension_overrides.items():
            result = pb.create_binding(conn, **valid_kwargs(**overrides))
            assert result["conflict"] is True, f"expected conflict for {dimension}"
            assert dimension in result["violations"], (
                f"expected {dimension} in violations, got {list(result['violations'].keys())}"
            )
            assert result["violations"][dimension] == original_id
            assert len(result["violations"]) == 1, (
                f"expected exactly 1 violation for {dimension}, got {len(result['violations'])}"
            )

        assert row_count(conn) == 1


# =============================================================================
# P1 — Core Persistence, Read, Identity
# =============================================================================


@requires_bindings_module
class TestCreateReadRestart:
    def test_fresh_create_persists_normalized_row_with_stable_id(self, conn):
        """2.1A-INT-001 (AC1/R-001/R-007): a fresh all-field create persists
        one normalized row and returns a stable id on success."""
        result = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/a/../a/"))
        assert result["conflict"] is False
        assert result["id"].startswith("pb_")

        row = get_row(conn, result["id"])
        assert row["bound_project_cwd"] == "/tmp/a"

    def test_new_connection_reads_unchanged_id_and_every_field(self, db_path):
        """2.1A-INT-002 (AC1/AC3/R-007): closing and reopening a new
        connection to the same db_path ("restart") returns the identical id
        and every public field exactly."""
        conn1 = pb.connect(db_path=db_path)
        try:
            created = pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            binding = pb.get_binding(conn2, created["id"])
        finally:
            conn2.close()

        assert binding is not None
        assert binding.id == created["id"]
        expected = valid_kwargs()
        as_dict = binding.to_dict()
        assert as_dict["profile"] == expected["profile"]
        assert as_dict["display_name"] == expected["display_name"]
        assert as_dict["bound_project_cwd"] == expected["bound_project_cwd"]
        assert as_dict["github_reference"] == expected["github_reference"]
        assert as_dict["bmad_skill_dir"] == expected["bmad_skill_dir"]
        assert as_dict["provider_name"] == expected["provider_name"]
        assert as_dict["provider_binding_name"] == expected["provider_binding_name"]
        assert as_dict["provider_metadata"] == expected["provider_metadata"]

    def test_unknown_binding_id_returns_none_without_mutation(self, conn):
        """2.1A-INT-003 (AC3): reading an unknown id returns None."""
        assert pb.get_binding(conn, "pb_doesnotexist") is None

    def test_profile_list_returns_only_that_profile(self, conn):
        """2.1A-INT-004 (AC3/R-009): list_bindings_for_profile filters by
        profile and returns every public field for the rows it does return."""
        pb.create_binding(conn, **valid_kwargs(profile="alpha", bound_project_cwd="/tmp/alpha"))
        pb.create_binding(conn, **valid_kwargs(profile="beta", bound_project_cwd="/tmp/beta"))

        alpha_rows = pb.list_bindings_for_profile(conn, "alpha")
        assert len(alpha_rows) == 1
        assert alpha_rows[0].bound_project_cwd == "/tmp/alpha"


@requires_bindings_module
class TestRequiredFieldValidationP1:
    def test_reject_blank_profile_zero_mutation(self, conn):
        """2.1A-INT-005 (R-001)."""
        with pytest.raises(ValueError):
            pb.create_binding(conn, **valid_kwargs(profile="  "))
        assert row_count(conn) == 0

    def test_reject_blank_display_name_zero_mutation(self, conn):
        """2.1A-INT-006 (R-001)."""
        with pytest.raises(ValueError):
            pb.create_binding(conn, **valid_kwargs(display_name=""))
        assert row_count(conn) == 0

    @pytest.mark.parametrize(
        "field,bad_value",
        [
            ("display_name", None),
            ("bound_project_cwd", None),
            ("profile", 123),
            ("bound_project_cwd", ["/tmp/a"]),
        ],
        ids=[
            "display-name-none",
            "cwd-none",
            "profile-int",
            "cwd-list",
        ],
    )
    def test_reject_none_or_unsupported_required_field_type(self, conn, field, bad_value):
        """2.1A-INT-008 (R-001/R-010): None/unsupported types on required
        fields must raise, never be misreported as an ordinary conflict."""
        with pytest.raises((ValueError, TypeError)):
            pb.create_binding(conn, **valid_kwargs(**{field: bad_value}))
        assert row_count(conn) == 0


@requires_bindings_module
class TestUniquenessAndNormalization:
    def test_multiple_rows_with_all_optional_refs_null_are_allowed(self, conn):
        """2.1A-INT-009 (AC1/R-002): optional NULL fields never collide with
        each other via the partial unique indexes."""
        first = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/one",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
        )
        second = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/two",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
        )
        assert first["conflict"] is False
        assert second["conflict"] is False
        assert row_count(conn) == 2

    @pytest.mark.parametrize(
        "spelling_a,spelling_b",
        [
            ("/tmp/proj", "/tmp/proj/"),
            ("/tmp/proj", "/tmp/other/../proj"),
        ],
        ids=["trailing-slash", "dot-dot-collapse"],
    )
    def test_equivalent_cwd_spellings_collide(self, conn, spelling_a, spelling_b):
        """2.1A-INT-010 (AC2/R-002)."""
        first = pb.create_binding(conn, **valid_kwargs(bound_project_cwd=spelling_a))
        assert first["conflict"] is False
        second = pb.create_binding(conn, **valid_kwargs(bound_project_cwd=spelling_b))
        assert second["conflict"] is True
        assert second["violations"]["bound_project_cwd"] == first["id"]

    def test_equivalent_bmad_dir_spellings_collide(self, conn):
        """2.1A-INT-011 (AC2/R-002)."""
        first = pb.create_binding(
            conn,
            **valid_kwargs(bound_project_cwd="/tmp/a", bmad_skill_dir="/tmp/a/_bmad"),
        )
        second = pb.create_binding(
            conn,
            **valid_kwargs(bound_project_cwd="/tmp/b", bmad_skill_dir="/tmp/a/_bmad/"),
        )
        assert first["conflict"] is False
        assert second["conflict"] is True
        assert second["violations"]["bmad_skill_dir"] == first["id"]

    def test_filesystem_root_remains_root_after_normalization(self, conn):
        """2.1A-INT-012 (R-002/R-012): normalizing "/" must not strip it down
        to an empty string (which would corrupt the NOT NULL/uniqueness
        contract)."""
        result = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/"))
        assert result["conflict"] is False
        row = get_row(conn, result["id"])
        assert row["bound_project_cwd"] == "/"

    @pytest.mark.parametrize(
        "raw_path,expected",
        [
            ("~/proj", str(Path.home() / "proj")),
            ("/a/./b", "/a/b"),
            ("/a/b/", "/a/b"),
            ("/", "/"),
        ],
        ids=["expanduser", "dot-segment", "trailing-slash", "root"],
    )
    def test_path_normalization_matrix(self, conn, raw_path, expected):
        """2.1A-UNIT-001 (R-002/R-012): exercised through create+read since the
        story does not commit to a public path-helper name; expand-user,
        relative/dot segments, trailing separators, and root must each
        normalize as documented."""
        result = pb.create_binding(conn, **valid_kwargs(bound_project_cwd=raw_path))
        row = get_row(conn, result["id"])
        assert row["bound_project_cwd"] == expected


@requires_bindings_module
class TestGithubReferenceCanonicalization:
    @pytest.mark.parametrize(
        "malformed",
        [
            {"owner": "NousResearch"},
            {"repo": "hermes-agent"},
            {"owner": "", "repo": "hermes-agent"},
            {"owner": "NousResearch", "repo": ""},
            "NousResearch/hermes-agent",
            {},
        ],
        ids=[
            "missing-repo",
            "missing-owner",
            "blank-owner",
            "blank-repo",
            "bare-string",
            "empty-object",
        ],
    )
    def test_reject_malformed_github_reference_zero_mutation(self, conn, malformed):
        """2.1A-INT-014 (R-003/R-010)."""
        with pytest.raises(ValueError):
            pb.create_binding(conn, **valid_kwargs(github_reference=malformed))
        assert row_count(conn) == 0

    def test_valid_github_json_preserved_exactly_with_separate_canonical_key(self, conn):
        """2.1A-INT-015 (AC3/R-003): the stored github_reference JSON is
        preserved verbatim on read while uniqueness uses a separate canonical
        key column, not the JSON text."""
        reference = {"owner": "NousResearch", "repo": "Hermes-Agent"}
        result = pb.create_binding(conn, **valid_kwargs(github_reference=reference))
        binding = pb.get_binding(conn, result["id"])
        assert binding.to_dict()["github_reference"] == reference


@requires_bindings_module
class TestProviderIdentityAndFixtureRoundtrip:
    def test_real_provider_fixture_roundtrips_after_restart(self, db_path):
        """2.1A-INT-016 (AC1/AC3/R-004/R-013): load the shipped Workflow
        Commander v1 fixture, persist the generic provider/name tuple plus
        opaque metadata, restart, and compare exactly."""
        fixture = load_status_valid_fixture()
        binding_ref = fixture["bindingRef"]

        conn1 = pb.connect(db_path=db_path)
        try:
            created = pb.create_binding(
                conn1,
                **valid_kwargs(
                    provider_name=binding_ref["provider"],
                    provider_binding_name=binding_ref["name"],
                    provider_metadata={
                        "bindingId": binding_ref["bindingId"],
                        "projectRef": binding_ref["projectRef"],
                    },
                ),
            )
        finally:
            conn1.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            binding = pb.get_binding(conn2, created["id"])
        finally:
            conn2.close()

        as_dict = binding.to_dict()
        assert as_dict["provider_name"] == binding_ref["provider"]
        assert as_dict["provider_binding_name"] == binding_ref["name"]
        assert as_dict["provider_metadata"] == {
            "bindingId": binding_ref["bindingId"],
            "projectRef": binding_ref["projectRef"],
        }

    def test_distinct_complete_provider_tuples_are_allowed(self, conn):
        """2.1A-INT-018 (R-004)."""
        first = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/a",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name="archon",
                provider_binding_name="engine-a",
            ),
        )
        second = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/b",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name="archon",
                provider_binding_name="engine-b",
            ),
        )
        assert first["conflict"] is False
        assert second["conflict"] is False

    def test_blank_provider_identity_coerced_to_none_no_collision(self, conn):
        """Finding 22: blank provider_name/provider_binding_name are coerced
        to None, so two bindings with blank provider identity don't collide
        on the provider dimension (NULL doesn't trigger the partial unique
        index)."""
        first = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/a",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name="",
                provider_binding_name="",
                provider_metadata=None,
            ),
        )
        second = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/b",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name="   ",
                provider_binding_name="   ",
                provider_metadata=None,
            ),
        )
        assert first["conflict"] is False
        assert second["conflict"] is False
        assert row_count(conn) == 2

        first_binding = pb.get_binding(conn, first["id"])
        assert first_binding.provider_name is None
        assert first_binding.provider_binding_name is None


@requires_bindings_module
class TestConflictAggregationAndRetryDiscipline:
    def test_candidate_colliding_on_all_dimensions_reports_all_and_no_row(self, conn):
        """2.1A-INT-020 (AC2/R-005): a candidate that collides on every
        dimension at once returns all dimension->id entries and persists no
        additional row."""
        original = pb.create_binding(conn, **valid_kwargs())
        result = pb.create_binding(conn, **valid_kwargs())
        assert result["conflict"] is True
        assert set(result["violations"]) == {
            "bound_project_cwd",
            "github_reference_key",
            "bmad_skill_dir",
            "provider_identity",
        }
        assert all(v == original["id"] for v in result["violations"].values())
        assert row_count(conn) == 1

    def test_exact_duplicate_action_conflicts_no_suffix_no_retry(self, conn):
        """2.1A-INT-021 (AC2/R-005): repeating the exact same create call
        must conflict — never auto-suffix, dedupe, or silently retry the way
        `_unique_slug()` does for project slugs."""
        pb.create_binding(conn, **valid_kwargs())
        result = pb.create_binding(conn, **valid_kwargs())
        assert result["conflict"] is True
        assert row_count(conn) == 1

    def test_same_identity_values_different_profiles_are_allowed(self, conn):
        """2.1A-INT-022 (AC2/R-002/R-009): uniqueness is profile-scoped, not
        global — identical cwd/github/bmad/provider values under different
        profiles must both persist."""
        first = pb.create_binding(conn, **valid_kwargs(profile="alpha"))
        second = pb.create_binding(conn, **valid_kwargs(profile="beta"))
        assert first["conflict"] is False
        assert second["conflict"] is False
        assert row_count(conn) == 2

    def test_forced_precheck_miss_still_conflicts_via_real_unique_index(
        self, conn, monkeypatch
    ):
        """2.1A-INT-023 (AC2/R-006): if the pre-check SELECT dimension pass is
        forced to report a miss (simulating a race window), the real partial
        unique index on the INSERT must still catch the collision and the
        post-INSERT race check must report it as a structured conflict rather
        than an escaped IntegrityError. The monkeypatch only defeats the first
        call (the pre-check inside the transaction); the race-check call after
        IntegrityError uses the real function, proving the fail-safe works."""
        pb.create_binding(conn, **valid_kwargs())

        precheck_name = "_check_uniqueness_dimensions"
        if hasattr(pb, precheck_name):
            real_check = getattr(pb, precheck_name)
            call_count = {"n": 0}

            def _flaky_precheck(*args, **kwargs):
                call_count["n"] += 1
                if call_count["n"] == 1:
                    return {}
                return real_check(*args, **kwargs)

            monkeypatch.setattr(pb, precheck_name, _flaky_precheck)

        result = pb.create_binding(conn, **valid_kwargs())
        assert result["conflict"] is True
        assert row_count(conn) == 1


def _race_worker(hermes_home: str, db_path_str: str, result_path: str, barrier_path: str) -> None:
    """Subprocess body for cross-process create_binding races (module-level
    for pickling under the ``spawn`` start method)."""
    os.environ["HERMES_HOME"] = hermes_home
    sys.path.insert(0, str(REPO_ROOT))
    from hermes_project_work import bindings as worker_pb

    while not os.path.exists(barrier_path):
        time.sleep(0.001)

    conn = worker_pb.connect(db_path=Path(db_path_str))
    try:
        result = worker_pb.create_binding(conn, **valid_kwargs())
    finally:
        conn.close()
    Path(result_path).write_text(json.dumps(result))


def _distinct_race_worker(
    hermes_home: str, db_path_str: str, cwd: str, result_path: str, barrier_path: str
) -> None:
    os.environ["HERMES_HOME"] = hermes_home
    sys.path.insert(0, str(REPO_ROOT))
    from hermes_project_work import bindings as worker_pb

    while not os.path.exists(barrier_path):
        time.sleep(0.001)

    conn = worker_pb.connect(db_path=Path(db_path_str))
    try:
        result = worker_pb.create_binding(
            conn,
            profile="default",
            display_name="Race Test",
            bound_project_cwd=cwd,
        )
    finally:
        conn.close()
    Path(result_path).write_text(json.dumps(result))


@requires_bindings_module
class TestCrossProcessRaces:
    def test_two_processes_race_on_one_identity_one_wins_one_conflicts(
        self, tmp_path
    ):
        """2.1A-INT-024 (AC2/R-006): two real OS processes call
        create_binding() with the identical identity at ~the same instant —
        exactly one succeeds, the other reports a structured conflict, and
        exactly one row persists. Mirrors the barrier-file pattern in
        tests/stress/test_atypical_scenarios.py::_idempotency_race_worker.
        Finding 35: no longer requires HERMES_HOME from the parent — the
        test creates a temp dir and passes it as the subprocess HERMES_HOME."""
        db_file = tmp_path / "project_bindings.db"
        barrier = tmp_path / "barrier"
        results = [tmp_path / f"race_result_{i}.json" for i in range(2)]
        hermes_home_dir = tmp_path / "hermes_home"
        hermes_home_dir.mkdir()
        ctx = mp.get_context("spawn")
        hermes_home = str(hermes_home_dir)
        procs = [
            ctx.Process(
                target=_race_worker,
                args=(hermes_home, str(db_file), str(results[i]), str(barrier)),
            )
            for i in range(2)
        ]
        for proc in procs:
            proc.start()
        time.sleep(0.1)
        barrier.write_text("go")
        for proc in procs:
            proc.join(timeout=10)

        outcomes = [json.loads(r.read_text()) for r in results if r.exists()]
        assert len(outcomes) == 2, f"expected 2 outcomes, got {len(outcomes)}"
        conflicts = [o["conflict"] for o in outcomes]
        assert sorted(conflicts) == [False, True], (
            f"expected exactly one success and one conflict, got {conflicts}"
        )

        conflict_outcome = next(o for o in outcomes if o["conflict"])
        assert "violations" in conflict_outcome, (
            "conflict outcome must include violations field"
        )
        assert len(conflict_outcome["violations"]) > 0, (
            "conflict outcome must report at least one violated dimension"
        )

        conn = pb.connect(db_path=db_file)
        try:
            assert row_count(conn) == 1
        finally:
            conn.close()

    def test_two_processes_create_distinct_identities_both_persist(self, tmp_path):
        """2.1A-INT-025 (R-006/R-014): two processes creating two distinct
        identities concurrently must both persist and both read back after
        reopen — concurrency must not corrupt unrelated rows.
        Finding 35: no longer requires HERMES_HOME from the parent."""
        db_file = tmp_path / "project_bindings.db"
        barrier = tmp_path / "barrier"
        results = [tmp_path / f"distinct_result_{i}.json" for i in range(2)]
        cwds = ["/tmp/race-distinct-a", "/tmp/race-distinct-b"]
        hermes_home_dir = tmp_path / "hermes_home"
        hermes_home_dir.mkdir()
        ctx = mp.get_context("spawn")
        hermes_home = str(hermes_home_dir)
        procs = [
            ctx.Process(
                target=_distinct_race_worker,
                args=(
                    hermes_home,
                    str(db_file),
                    cwds[i],
                    str(results[i]),
                    str(barrier),
                ),
            )
            for i in range(2)
        ]
        for proc in procs:
            proc.start()
        time.sleep(0.1)
        barrier.write_text("go")
        for proc in procs:
            proc.join(timeout=10)

        outcomes = [json.loads(r.read_text()) for r in results if r.exists()]
        assert len(outcomes) == 2, f"expected 2 outcomes, got {len(outcomes)}"
        assert all(o["conflict"] is False for o in outcomes), (
            f"expected both processes to succeed, got {outcomes}"
        )
        assert all("id" in o for o in outcomes), (
            "success outcomes must include id field"
        )
        ids = [o["id"] for o in outcomes]
        assert len(set(ids)) == 2, f"expected 2 distinct ids, got {ids}"

        conn = pb.connect(db_path=db_file)
        try:
            assert row_count(conn) == 2
            for binding_id in ids:
                binding = pb.get_binding(conn, binding_id)
                assert binding is not None, f"binding {binding_id} not found after reopen"
        finally:
            conn.close()


@requires_bindings_module
class TestProfileIsolation:
    def test_mixed_profile_explicit_db_list_filters_correctly(self, conn):
        """2.1A-INT-026 (AC3/R-009)."""
        _minimal = dict(github_reference=None, bmad_skill_dir=None,
                        provider_name=None, provider_binding_name=None,
                        provider_metadata=None)
        pb.create_binding(conn, **valid_kwargs(profile="alpha", bound_project_cwd="/tmp/a", **_minimal))
        pb.create_binding(conn, **valid_kwargs(profile="alpha", bound_project_cwd="/tmp/a2", **_minimal))
        pb.create_binding(conn, **valid_kwargs(profile="beta", bound_project_cwd="/tmp/b", **_minimal))

        alpha = pb.list_bindings_for_profile(conn, "alpha")
        beta = pb.list_bindings_for_profile(conn, "beta")
        assert len(alpha) == 2
        assert len(beta) == 1

    def test_db_path_resolves_under_context_local_profile_home(self, tmp_path):
        """2.1A-INT-027 (R-009): project_bindings_db_path() resolves under
        whatever context-local/temp Hermes home is active, using the same
        override helper as production code
        (hermes_constants.set_hermes_home_override), never a hardcoded
        ``~/.hermes``."""
        from hermes_constants import reset_hermes_home_override, set_hermes_home_override

        fake_home = tmp_path / "profile-a"
        fake_home.mkdir()
        token = set_hermes_home_override(str(fake_home))
        try:
            assert pb.project_bindings_db_path() == fake_home / "project_bindings.db"
        finally:
            reset_hermes_home_override(token)

    def test_active_profile_stores_correctly_resolver_exception_falls_back_default(
        self, conn, monkeypatch
    ):
        """2.1A-INT-028 (AC1/R-009): the stored `profile` column is resolved
        via hermes_cli.profiles.get_active_profile_name(); when that resolver
        raises, the documented fallback is the literal string "default"."""
        import hermes_cli.profiles as profiles_mod

        def _boom():
            raise RuntimeError("boom")

        monkeypatch.setattr(profiles_mod, "get_active_profile_name", _boom)
        result = pb.create_binding(conn, **valid_kwargs(profile=None))
        binding = pb.get_binding(conn, result["id"])
        assert binding.to_dict()["profile"] == "default"

    def test_separate_profile_homes_cannot_read_each_others_bindings(self, tmp_path):
        """2.1A-INT-029 (AC1/R-009): two distinct profile homes (two distinct
        db_path values, standing in for two HERMES_HOME profiles) never see
        each other's rows — mirrors
        tests/hermes_cli/test_projects_db.py::test_per_profile_isolation."""
        conn_a = pb.connect(db_path=tmp_path / "a" / "project_bindings.db")
        conn_b = pb.connect(db_path=tmp_path / "b" / "project_bindings.db")
        try:
            created = pb.create_binding(conn_a, **valid_kwargs())
            assert pb.get_binding(conn_b, created["id"]) is None
        finally:
            conn_a.close()
            conn_b.close()

    def test_list_bindings_for_profile_normalizes_whitespace(self, conn):
        """Finding 39: list_bindings_for_profile strips whitespace from the
        profile parameter, matching the canonicalization done by
        _resolve_profile during create. Without normalization, ' alpha '
        would return empty results even though bindings exist for 'alpha'."""
        _minimal = dict(github_reference=None, bmad_skill_dir=None,
                        provider_name=None, provider_binding_name=None,
                        provider_metadata=None)
        pb.create_binding(conn, **valid_kwargs(profile="alpha", bound_project_cwd="/tmp/a", **_minimal))

        result = pb.list_bindings_for_profile(conn, "  alpha  ")
        assert len(result) == 1
        assert result[0].profile == "alpha"

    def test_list_bindings_for_profile_rejects_non_string(self, conn):
        """Finding 39: list_bindings_for_profile rejects non-string profile
        values with TypeError, matching create_binding's profile validation."""
        with pytest.raises(TypeError):
            pb.list_bindings_for_profile(conn, 123)


@requires_bindings_module
class TestMigrationAndIdempotentInit:
    def test_reopen_current_schema_twice_without_data_loss_or_error(self, db_path):
        """2.1A-INT-030 (AC4/R-008)."""
        conn1 = pb.connect(db_path=db_path)
        try:
            created = pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb.get_binding(conn2, created["id"]) is not None
        finally:
            conn2.close()

    def test_migration_seam_invoked_on_every_connect_including_cached(self, db_path, monkeypatch):
        """2.1A-INT-031 (AC4/R-008): _migrate_add_optional_columns() (or
        whatever the migration seam is ultimately named) runs on every
        connect() call, even when the schema-init cache is already warm for
        this path."""
        migrate_name = "_migrate_add_optional_columns"
        if not hasattr(pb, migrate_name):
            pytest.skip(f"pb.{migrate_name} not present; adjust to actual migration seam name")

        calls = []
        original = getattr(pb, migrate_name)

        def _wrapped(conn_):
            calls.append(1)
            return original(conn_)

        monkeypatch.setattr(pb, migrate_name, _wrapped)

        pb.connect(db_path=db_path).close()
        pb.connect(db_path=db_path).close()

        assert len(calls) == 2

    def test_clear_init_cache_new_process_simulation_preserves_schema(self, db_path):
        """2.1A-INT-032 (AC4/R-008): clearing the module's per-path
        initialized-paths cache (simulating a fresh process) and reconnecting
        must not lose data or re-raise "duplicate column"/"duplicate table"."""
        conn1 = pb.connect(db_path=db_path)
        try:
            created = pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        if hasattr(pb, "_INITIALIZED_PATHS"):
            pb._INITIALIZED_PATHS.clear()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb.get_binding(conn2, created["id"]) is not None
        finally:
            conn2.close()

    def test_concurrent_first_connects_all_close_cleanly(self, db_path):
        """2.1A-INT-033 (AC4/R-008, threaded): several threads calling
        connect() against a brand-new db_path for the first time must all
        succeed and leave one consistent, usable schema — no
        "table already exists" crash from a racing CREATE TABLE."""
        errors = []
        conns = []
        lock = threading.Lock()

        def _connect():
            try:
                c = pb.connect(db_path=db_path)
                with lock:
                    conns.append(c)
            except Exception as exc:  # noqa: BLE001 - captured for assertion
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_connect) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        try:
            assert not errors, f"connect() raised under concurrent first-open: {errors}"
            assert len(conns) == 8
        finally:
            for c in conns:
                c.close()

    def test_cached_path_whose_file_is_recreated_does_not_error(self, db_path):
        """2.1A-INT-034 (R-008): if the on-disk file behind a cached path is
        deleted and recreated (e.g. by an external tool), the next connect()
        through the same process must not raise "no such table" — either by
        detecting the recreation or by re-running the idempotent schema
        script defensively."""
        conn1 = pb.connect(db_path=db_path)
        conn1.close()

        db_path.unlink()

        conn2 = pb.connect(db_path=db_path)
        try:
            result = pb.create_binding(conn2, **valid_kwargs())
            assert result["conflict"] is False
        finally:
            conn2.close()

    def test_cached_connection_detects_missing_table_and_repairs(self, db_path):
        """Finding 27: _init_cached_connection verifies the COMPLETE schema
        via _verify_complete_schema. When the table is missing entirely
        (PRAGMA table_info returns no rows), the cached path re-runs
        executescript(SCHEMA_SQL) to recreate it."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        # Drop the table entirely — simulates external deletion
        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP TABLE project_bindings")
            conn_alter.commit()
        finally:
            conn_alter.close()

        # Reconnect through the cached path — _verify_complete_schema must
        # detect the missing table and re-run executescript(SCHEMA_SQL).
        conn2 = pb.connect(db_path=db_path)
        try:
            columns = {
                row["name"]
                for row in conn2.execute("PRAGMA table_info(project_bindings)")
            }
            assert "github_reference" in columns, (
                "schema verification should have restored the missing table"
            )
            assert "github_reference_key" in columns
            assert "bmad_skill_dir" in columns
            # Verify the connection is usable after repair
            result = pb.create_binding(conn2, **valid_kwargs())
            assert result["conflict"] is False
        finally:
            conn2.close()

    def test_verify_complete_schema_rejects_missing_table(self, db_path):
        """Finding 27: _verify_complete_schema returns False when the table
        does not exist (PRAGMA table_info returns no rows)."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP TABLE project_bindings")
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_verify_complete_schema_detects_missing_indexes(self, db_path):
        """Finding 33: _verify_complete_schema returns False when a unique
        index has been dropped externally — column-only verification would
        miss this and the uniqueness constraints would silently vanish."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_cached_connection_repairs_dropped_indexes(self, db_path):
        """Finding 33: when a unique index is dropped externally, the cached
        connection path detects the incomplete schema via
        _verify_complete_schema and re-runs executescript(SCHEMA_SQL) to
        recreate the missing index additively."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True, (
                "cached connection should have repaired the dropped index"
            )
            indexes = {
                row["name"]
                for row in conn2.execute("PRAGMA index_list(project_bindings)").fetchall()
            }
            assert "uq_pb_profile_cwd" in indexes, (
                "dropped index should have been recreated by schema repair"
            )
        finally:
            conn2.close()

    def test_verify_complete_schema_detects_non_unique_index(self, db_path):
        """Finding 36: _verify_complete_schema returns False when an expected
        unique index exists by name but is not actually unique — name-only
        verification would miss a broken index recreated without UNIQUE."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn.execute(
                "CREATE INDEX uq_pb_profile_cwd"
                " ON project_bindings(profile, bound_project_cwd)"
            )
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_verify_complete_schema_detects_missing_where_clause(self, db_path):
        """Finding 43: _verify_complete_schema returns False when a partial
        index exists by name with correct columns and unique flag but is
        missing the WHERE clause — the uniqueness constraint would apply to
        NULL values, breaking partial index semantics."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP INDEX IF EXISTS uq_pb_profile_github_key")
            conn.execute(
                "CREATE UNIQUE INDEX uq_pb_profile_github_key"
                " ON project_bindings(profile, github_reference_key)"
            )
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_pragma_relationships_prove_columns_and_unique_predicates(self, conn):
        """2.1A-INT-035 (AC4/R-002/R-008): assert the schema's structural
        shape via PRAGMA introspection (required columns + four partial
        unique indexes), not a brittle row-count/enumeration snapshot."""
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(project_bindings)")}
        required_columns = {
            "id",
            "profile",
            "display_name",
            "bound_project_cwd",
            "github_reference",
            "github_reference_key",
            "bmad_skill_dir",
            "provider_name",
            "provider_binding_name",
            "provider_metadata",
            "created_at",
        }
        assert required_columns.issubset(columns)

        indexes = conn.execute("PRAGMA index_list(project_bindings)").fetchall()
        index_map = {row["name"]: row for row in indexes}
        expected_unique_indexes = {
            "uq_pb_profile_cwd",
            "uq_pb_profile_github_key",
            "uq_pb_profile_bmad_dir",
            "uq_pb_profile_provider",
        }
        for name in expected_unique_indexes:
            assert name in index_map, f"expected index {name} not found"
            assert index_map[name]["unique"] == 1, f"index {name} is not unique"


@requires_bindings_module
class TestJsonUnicodeAndCorruptionHandling:
    def test_nested_unicode_json_null_arrays_survive_exact_roundtrip(self, conn):
        """2.1A-INT-037 (AC3/R-007/R-010): non-ASCII text, JSON null, and
        nested arrays inside provider_metadata survive an exact restart
        round-trip (guards the project's encoding-explicit-I/O rule)."""
        metadata = {
            "bindingId": "wpb_héllo_wörld_日本語",
            "tags": ["a", None, {"nested": ["b", "c"]}],
            "note": None,
        }
        result = pb.create_binding(conn, **valid_kwargs(provider_metadata=metadata))
        binding = pb.get_binding(conn, result["id"])
        assert binding.to_dict()["provider_metadata"] == metadata

    @pytest.mark.parametrize(
        "non_serializable",
        [
            {"circular": object()},
            {"nan": float("nan")},
        ],
        ids=["non-serializable-object", "non-standard-json-constant"],
    )
    def test_reject_non_serializable_or_non_standard_json_before_insert(
        self, conn, non_serializable
    ):
        """2.1A-INT-038 (R-010): reject before INSERT, not after a partial
        write or a silently-substituted value."""
        with pytest.raises((ValueError, TypeError)):
            pb.create_binding(conn, **valid_kwargs(provider_metadata=non_serializable))
        assert row_count(conn) == 0

    @pytest.mark.parametrize(
        "bad_metadata",
        [
            {"key": b"bytes_value"},
            {"key": {1, 2, 3}},
            {"key": object()},
            {"nested": {"deep": b"nope"}},
            {"list_with_bytes": [b"nope"]},
        ],
        ids=[
            "bytes-value",
            "set-value",
            "object-value",
            "nested-bytes",
            "list-with-bytes",
        ],
    )
    def test_reject_non_json_native_types_in_provider_metadata_before_serialize(
        self, conn, bad_metadata
    ):
        """Finding 26: provider_metadata with non-JSON-native types (bytes,
        sets, custom objects) is rejected by _require_json_compatible before
        reaching json.dumps — TypeError, not ValueError, and zero rows."""
        with pytest.raises(TypeError):
            pb.create_binding(conn, **valid_kwargs(provider_metadata=bad_metadata))
        assert row_count(conn) == 0

    @pytest.mark.parametrize(
        "bad_metadata",
        [
            {"key": float("inf")},
            {"key": float("-inf")},
            {"key": float("nan")},
            {"nested": {"deep": float("inf")}},
            {"list_with_inf": [float("inf")]},
        ],
        ids=[
            "inf-value",
            "neg-inf-value",
            "nan-value",
            "nested-inf",
            "list-with-inf",
        ],
    )
    def test_reject_non_finite_floats_in_provider_metadata(
        self, conn, bad_metadata
    ):
        """Finding 34: non-finite floats (inf, -inf, nan) are valid Python
        float instances but are not representable in JSON. _require_json_compatible
        must reject them with TypeError before reaching json.dumps, giving a
        specific error about non-finite values rather than a generic
        serialization error."""
        with pytest.raises(TypeError, match="non-finite float"):
            pb.create_binding(conn, **valid_kwargs(provider_metadata=bad_metadata))
        assert row_count(conn) == 0

    def test_reject_cyclic_reference_in_provider_metadata(self, conn):
        """Finding 44: _require_json_compatible must detect cyclic references
        and reject them with TypeError before reaching json.dumps, which would
        raise RecursionError. Cyclic references are not JSON-serializable."""
        cyclic_dict = {}
        cyclic_dict["self"] = cyclic_dict
        with pytest.raises(TypeError, match="cyclic reference"):
            pb.create_binding(conn, **valid_kwargs(provider_metadata=cyclic_dict))
        assert row_count(conn) == 0

        cyclic_list = []
        cyclic_list.append(cyclic_list)
        with pytest.raises(TypeError, match="cyclic reference"):
            pb.create_binding(conn, **valid_kwargs(provider_metadata={"nested": cyclic_list}))
        assert row_count(conn) == 0

    def test_corrupt_stored_json_fails_explicitly_on_read(self, conn):
        """2.1A-INT-039 (R-010): if a row's JSON column is corrupted by an
        out-of-band write, get_binding() must raise explicitly rather than
        silently substituting None/empty data."""
        result = pb.create_binding(conn, **valid_kwargs())
        conn.execute(
            "UPDATE project_bindings SET provider_metadata = ? WHERE id = ?",
            ("{not valid json", result["id"]),
        )
        conn.commit()
        with pytest.raises((ValueError, json.JSONDecodeError)):
            pb.get_binding(conn, result["id"])


@requires_bindings_module
class TestIdentityStability:
    def test_stored_id_not_recomputed_from_changed_input(self, conn):
        """2.1A-INT-040 (AC1/R-007): re-reading a binding after a fresh
        connect must not recompute its id from cwd/profile/artifact-path the
        way Story 2.5's derived identity would — the persisted random id is
        authoritative and never changes."""
        result = pb.create_binding(conn, **valid_kwargs())
        first_read = pb.get_binding(conn, result["id"])
        second_read = pb.get_binding(conn, result["id"])
        assert first_read.id == second_read.id == result["id"]

    def test_random_id_format_independent_of_inputs(self, conn):
        """2.1A-UNIT-003 (R-007/R-011): id format (``pb_`` + hex) is stable
        and does not vary with profile/cwd/artifact content."""
        first = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/x"))
        second = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/y", profile="other"))
        assert re.match(r"^pb_[0-9a-f]+$", first["id"])
        assert re.match(r"^pb_[0-9a-f]+$", second["id"])
        assert first["id"] != second["id"]

    def test_forced_random_id_collision_preserves_first_row(self, conn, monkeypatch):
        """2.1A-INT-041 (R-011): if the random-id generator is forced to
        collide (pathological but possible), create_binding() must fail
        closed — never silently overwrite the first row.  Returns a
        machine-readable conflict with an "id" violation dimension."""
        id_gen_name = "_new_binding_id"
        if not hasattr(pb, id_gen_name):
            pytest.skip(f"pb.{id_gen_name} not present; adjust to actual id generator name")

        monkeypatch.setattr(pb, id_gen_name, lambda: "pb_00000000")

        first = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/first"))
        assert first["id"] == "pb_00000000"
        assert first["conflict"] is False

        # Second create with forced id collision: override ALL uniqueness dimensions
        # so the pre-check passes and the INSERT is attempted, forcing the PK collision.
        second_kwargs = valid_kwargs(
            bound_project_cwd="/tmp/second",
            github_reference=None,
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
            provider_metadata=None,
        )

        # PK collision returns a machine-readable conflict instead of raising
        result = pb.create_binding(conn, **second_kwargs)
        assert result["conflict"] is True
        assert "id" in result["violations"]
        assert result["violations"]["id"] == "pb_00000000"

        # Only the first row persists — the second create failed closed
        assert row_count(conn) == 1


@requires_bindings_module
class TestFailureInjectionAndRollback:
    def test_injected_insert_failure_rolls_back_zero_row_and_later_reuse_works(
        self, conn, monkeypatch
    ):
        """2.1A-INT-042 (AC2/R-005/R-010/R-014): a forced failure inside the
        write transaction must roll back cleanly (zero rows), surface the
        original error (not misreport it as a conflict), and not poison the
        identity for a later, successful create with the same inputs."""
        import contextlib

        real_write_txn = pb.write_txn
        state = {"raise_once": True}

        @contextlib.contextmanager
        def _flaky_write_txn(c):
            if state["raise_once"]:
                state["raise_once"] = False
                raise sqlite3.OperationalError("disk I/O error (injected)")
            with real_write_txn(c) as inner:
                yield inner

        monkeypatch.setattr(pb, "write_txn", _flaky_write_txn)

        with pytest.raises(sqlite3.OperationalError, match="disk I/O error"):
            pb.create_binding(conn, **valid_kwargs())
        assert row_count(conn) == 0

        result = pb.create_binding(conn, **valid_kwargs())
        assert result["conflict"] is False

    def test_held_immediate_lock_causes_bounded_failure_then_succeeds_after_release(
        self, db_path
    ):
        """2.1A-INT-043 (R-014): a second connection holding an IMMEDIATE
        write lock causes connect() to fail closed (not hang forever) within
        the bounded retry budget; releasing the lock lets a subsequent
        connect() succeed."""
        blocker = sqlite3.connect(str(db_path))
        blocker.execute("PRAGMA journal_mode=WAL")
        blocker.execute("BEGIN IMMEDIATE")

        with pytest.raises(sqlite3.OperationalError):
            pb.connect(db_path=db_path)

        blocker.execute("ROLLBACK")
        blocker.close()

        conn = pb.connect(db_path=db_path)
        try:
            result = pb.create_binding(conn, **valid_kwargs())
            assert result["conflict"] is False
        finally:
            conn.close()

    def test_invalid_parent_path_fails_without_poisoning_cache(self, tmp_path):
        """2.1A-INT-044 (R-014): connecting to a db_path whose parent cannot
        be created (e.g. a file occupies the parent segment) must fail
        without poisoning the init-cache for a later, valid path."""
        blocked_parent = tmp_path / "not-a-directory"
        blocked_parent.write_text("occupying the path segment")
        bad_path = blocked_parent / "project_bindings.db"

        with pytest.raises(OSError):
            pb.connect(db_path=bad_path)

        good_path = tmp_path / "actually" / "project_bindings.db"
        conn = pb.connect(db_path=good_path)
        try:
            result = pb.create_binding(conn, **valid_kwargs())
            assert result["conflict"] is False
        finally:
            conn.close()

    def test_foreign_keys_on_and_journal_mode_wal_or_documented_fallback(self, conn):
        """2.1A-INT-045 (R-013/R-014): PRAGMA foreign_keys must be on, and the
        journal mode must be WAL (or the documented DELETE fallback from
        hermes_state.apply_wal_with_fallback on WAL-incompatible filesystems)."""
        fk_state = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk_state == 1
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert journal_mode in ("wal", "delete")


@requires_bindings_module
class TestResourceHygiene:
    def test_connect_closing_closes_connection_on_exit(self, db_path):
        """2.1A-INT-036 (P2, Maintainability): connect_closing() guarantees
        the underlying sqlite3 connection is closed after the context exits,
        mirroring hermes_cli.projects_db.connect_closing."""
        with pb.connect_closing(db_path=db_path) as c:
            pb.create_binding(c, **valid_kwargs())
        with pytest.raises(sqlite3.ProgrammingError):
            c.execute("SELECT 1")


@requires_bindings_module
class TestSchemaVerificationCompleteness:
    """Finding 40: _verify_complete_schema must verify index column composition,
    not just index names and uniqueness flags."""

    def test_verify_complete_schema_detects_wrong_index_columns(self, db_path):
        """_verify_complete_schema returns False when an index has the right
        name and unique=1 but covers the wrong columns — name+unique-only
        verification would miss this."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn.execute(
                "CREATE UNIQUE INDEX uq_pb_profile_cwd"
                " ON project_bindings(profile)"
            )
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_verify_complete_schema_detects_wrong_column_order(self, db_path):
        """_verify_complete_schema returns False when an index covers the
        right columns but in the wrong order — column composition must match
        exactly, not just as a set."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP INDEX IF EXISTS uq_pb_profile_provider")
            conn.execute(
                "CREATE UNIQUE INDEX uq_pb_profile_provider"
                " ON project_bindings(provider_binding_name, provider_name, profile)"
                " WHERE provider_name IS NOT NULL AND provider_binding_name IS NOT NULL"
            )
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()


@requires_bindings_module
class TestProviderMetadataContradictoryKeys:
    """Finding 41: provider_metadata must not contain keys that overlap with
    the explicit Controller Identity columns (provider_name, provider_binding_name)."""

    def test_provider_metadata_with_provider_name_key_rejected(self, conn):
        """provider_metadata containing 'provider_name' key is rejected —
        this would contradict the explicit provider_name column."""
        metadata = {"provider_name": "other", "bindingId": "wpb_123"}
        with pytest.raises(ValueError, match="must not contain keys that overlap"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=metadata,
                )
            )
        assert row_count(conn) == 0

    def test_provider_metadata_with_provider_binding_name_key_rejected(self, conn):
        """provider_metadata containing 'provider_binding_name' key is rejected —
        this would contradict the explicit provider_binding_name column."""
        metadata = {"provider_binding_name": "other", "bindingId": "wpb_123"}
        with pytest.raises(ValueError, match="must not contain keys that overlap"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=metadata,
                )
            )
        assert row_count(conn) == 0

    def test_provider_metadata_with_both_contradictory_keys_rejected(self, conn):
        """provider_metadata containing both 'provider_name' and
        'provider_binding_name' keys is rejected."""
        metadata = {
            "provider_name": "other",
            "provider_binding_name": "other",
            "bindingId": "wpb_123",
        }
        with pytest.raises(ValueError, match="must not contain keys that overlap"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=metadata,
                )
            )
        assert row_count(conn) == 0


@requires_bindings_module
class TestSchemaPredicatesAndRollback:
    """Finding 42: Tests must verify schema predicates (partial index WHERE
    clauses), rollback behavior, and race timing."""

    def test_partial_index_predicate_allows_null_values_to_coexist(self, conn):
        """The partial unique indexes use WHERE ... IS NOT NULL predicates,
        allowing multiple bindings with NULL values in optional columns to
        coexist without collision. This verifies the predicate is enforced."""
        _minimal = dict(
            github_reference=None,
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
            provider_metadata=None,
        )
        result1 = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/a", **_minimal))
        result2 = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/b", **_minimal))

        assert result1["conflict"] is False
        assert result2["conflict"] is False
        assert row_count(conn) == 2

        binding1 = pb.get_binding(conn, result1["id"])
        binding2 = pb.get_binding(conn, result2["id"])
        assert binding1.github_reference is None
        assert binding2.github_reference is None

    def test_transaction_rollback_on_conflict_preserves_connection_state(self, conn):
        """When create_binding returns a conflict, the transaction is rolled
        back cleanly and the connection remains usable for subsequent operations."""
        _minimal = dict(
            github_reference=None,
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
            provider_metadata=None,
        )
        result1 = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/a", **_minimal))
        assert result1["conflict"] is False

        result2 = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/a", **_minimal))
        assert result2["conflict"] is True
        assert "bound_project_cwd" in result2["violations"]

        assert row_count(conn) == 1

        result3 = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/b", **_minimal))
        assert result3["conflict"] is False
        assert row_count(conn) == 2

    def test_cross_process_race_is_concurrent_not_sequential(self, tmp_path):
        """Cross-process race tests must verify that workers actually run
        concurrently, not sequentially. This test uses a barrier to ensure
        both workers attempt create_binding at the same instant."""
        db_file = tmp_path / "project_bindings.db"
        barrier = tmp_path / "barrier"
        results = [tmp_path / f"concurrent_result_{i}.json" for i in range(2)]
        hermes_home_dir = tmp_path / "hermes_home"
        hermes_home_dir.mkdir()
        ctx = mp.get_context("spawn")
        hermes_home = str(hermes_home_dir)

        procs = [
            ctx.Process(
                target=_race_worker,
                args=(hermes_home, str(db_file), str(results[i]), str(barrier)),
            )
            for i in range(2)
        ]
        for proc in procs:
            proc.start()

        time.sleep(0.1)
        barrier.write_text("go")

        for proc in procs:
            proc.join(timeout=10)

        outcomes = [json.loads(r.read_text()) for r in results if r.exists()]
        assert len(outcomes) == 2

        conflicts = [o["conflict"] for o in outcomes]
        assert sorted(conflicts) == [False, True]

        conn = pb.connect(db_path=db_file)
        try:
            assert row_count(conn) == 1
            binding = pb.get_binding(conn, next(o["id"] for o in outcomes if not o["conflict"]))
            assert binding is not None
            assert binding.profile == "default"
            assert binding.bound_project_cwd == "/tmp/hermes-agent"
        finally:
            conn.close()


@requires_bindings_module
class TestSchemaRepairVerification:
    """Finding 46/47/48: Schema repair must verify its own outcome, JSON
    column reads must validate types, and repair must work under lock."""

    def test_cached_connection_raises_when_repair_cannot_restore_schema(
        self, db_path, monkeypatch
    ):
        """Finding 46: _init_cached_connection must raise RuntimeError when
        schema repair executescript completes but _verify_complete_schema still
        returns False — silently returning a broken connection would let
        subsequent operations fail with confusing 'no such table' errors."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP TABLE project_bindings")
            conn_alter.commit()
        finally:
            conn_alter.close()

        real_verify = pb._verify_complete_schema
        call_count = {"n": 0}

        def _always_broken(conn):
            call_count["n"] += 1
            if call_count["n"] <= 1:
                return False
            return False

        monkeypatch.setattr(pb, "_verify_complete_schema", _always_broken)

        with pytest.raises(RuntimeError, match="schema repair completed but verification still failed"):
            pb.connect(db_path=db_path)

    def test_binding_from_row_rejects_non_dict_github_reference(self, conn):
        """Finding 47: _binding_from_row must validate that parsed JSON columns
        are dicts. If an external write stores a non-dict JSON value (e.g., a
        string or number), get_binding must raise ValueError rather than
        silently returning a ProjectBinding with wrong types."""
        result = pb.create_binding(conn, **valid_kwargs())

        conn.execute(
            "UPDATE project_bindings SET github_reference = ? WHERE id = ?",
            (json.dumps("not a dict"), result["id"]),
        )
        conn.commit()

        with pytest.raises(ValueError, match="github_reference must be a dict"):
            pb.get_binding(conn, result["id"])

    def test_binding_from_row_rejects_non_dict_provider_metadata(self, conn):
        """Finding 47: _binding_from_row must validate that provider_metadata
        is a dict after JSON parsing, not just any JSON value."""
        result = pb.create_binding(conn, **valid_kwargs())

        conn.execute(
            "UPDATE project_bindings SET provider_metadata = ? WHERE id = ?",
            (json.dumps([1, 2, 3]), result["id"]),
        )
        conn.commit()

        with pytest.raises(ValueError, match="provider_metadata must be a dict"):
            pb.get_binding(conn, result["id"])

    def test_schema_repair_under_lock_succeeds_after_lock_released(self, db_path):
        """Finding 48: when a cached connection needs schema repair and another
        connection holds an IMMEDIATE lock, the repair path must retry on lock
        errors (matching the cold path discipline) and succeed after the lock
        is released."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP TABLE project_bindings")
            conn_alter.commit()
        finally:
            conn_alter.close()

        blocker = sqlite3.connect(str(db_path))
        blocker.execute("BEGIN IMMEDIATE")

        import threading
        error_holder = []
        conn_holder = []

        def _try_connect():
            try:
                c = pb.connect(db_path=db_path)
                conn_holder.append(c)
            except Exception as exc:
                error_holder.append(exc)

        t = threading.Thread(target=_try_connect)
        t.start()
        time.sleep(0.2)

        blocker.execute("ROLLBACK")
        blocker.close()

        t.join(timeout=10)

        assert not error_holder, f"connect() raised under lock-during-repair: {error_holder}"
        assert conn_holder, "connect() did not return a connection"
        conn2 = conn_holder[0]
        try:
            assert pb._verify_complete_schema(conn2) is True
            result = pb.create_binding(conn2, **valid_kwargs())
            assert result["conflict"] is False
        finally:
            conn2.close()


@requires_bindings_module
class TestSchemaNotNullAndTypeVerification:
    """Finding 49: _verify_complete_schema must verify NOT NULL constraints
    and column type affinities, not just column names. A schema with correct
    column names but missing NOT NULL or wrong types would pass name-only
    verification while allowing invalid data."""

    def test_verify_complete_schema_detects_missing_not_null(self, db_path):
        """_verify_complete_schema returns False when a required NOT NULL
        column is recreated without the constraint — name-only verification
        would miss this and NULL values could be inserted into required
        fields."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP TABLE project_bindings")
            conn.executescript(pb.SCHEMA_SQL)
            conn.execute("DROP TABLE project_bindings")
            conn.executescript("""
                CREATE TABLE project_bindings (
                    id                      TEXT PRIMARY KEY,
                    profile                 TEXT NOT NULL,
                    display_name            TEXT,
                    bound_project_cwd       TEXT NOT NULL,
                    github_reference        TEXT,
                    github_reference_key    TEXT,
                    bmad_skill_dir          TEXT,
                    provider_name           TEXT,
                    provider_binding_name   TEXT,
                    provider_metadata       TEXT,
                    created_at              INTEGER NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_cwd
                    ON project_bindings(profile, bound_project_cwd);
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_github_key
                    ON project_bindings(profile, github_reference_key)
                    WHERE github_reference_key IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_bmad_dir
                    ON project_bindings(profile, bmad_skill_dir)
                    WHERE bmad_skill_dir IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_provider
                    ON project_bindings(profile, provider_name, provider_binding_name)
                    WHERE provider_name IS NOT NULL AND provider_binding_name IS NOT NULL;
            """)
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_verify_complete_schema_detects_wrong_column_type(self, db_path):
        """_verify_complete_schema returns False when a column has the wrong
        declared type — e.g. INTEGER instead of TEXT. Name-only verification
        would miss this and type-dependent operations would fail silently."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP TABLE project_bindings")
            conn.executescript("""
                CREATE TABLE project_bindings (
                    id                      TEXT PRIMARY KEY,
                    profile                 TEXT NOT NULL,
                    display_name            INTEGER NOT NULL,
                    bound_project_cwd       TEXT NOT NULL,
                    github_reference        TEXT,
                    github_reference_key    TEXT,
                    bmad_skill_dir          TEXT,
                    provider_name           TEXT,
                    provider_binding_name   TEXT,
                    provider_metadata       TEXT,
                    created_at              INTEGER NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_cwd
                    ON project_bindings(profile, bound_project_cwd);
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_github_key
                    ON project_bindings(profile, github_reference_key)
                    WHERE github_reference_key IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_bmad_dir
                    ON project_bindings(profile, bmad_skill_dir)
                    WHERE bmad_skill_dir IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_provider
                    ON project_bindings(profile, provider_name, provider_binding_name)
                    WHERE provider_name IS NOT NULL AND provider_binding_name IS NOT NULL;
            """)
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()

    def test_verify_complete_schema_accepts_lowercase_sqlite_type_names(self, db_path):
        """SQLite declared types are case-insensitive, so lower-case type
        names should satisfy the schema contract just like upper-case names."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP TABLE project_bindings")
            conn.executescript("""
                CREATE TABLE project_bindings (
                    id                      text PRIMARY KEY,
                    profile                 text NOT NULL,
                    display_name            text NOT NULL,
                    bound_project_cwd       text NOT NULL,
                    github_reference        text,
                    github_reference_key    text,
                    bmad_skill_dir          text,
                    provider_name           text,
                    provider_binding_name   text,
                    provider_metadata       text,
                    created_at              integer NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_cwd
                    ON project_bindings(profile, bound_project_cwd);
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_github_key
                    ON project_bindings(profile, github_reference_key)
                    WHERE github_reference_key IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_bmad_dir
                    ON project_bindings(profile, bmad_skill_dir)
                    WHERE bmad_skill_dir IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_provider
                    ON project_bindings(profile, provider_name, provider_binding_name)
                    WHERE provider_name IS NOT NULL AND provider_binding_name IS NOT NULL;
            """)
            assert pb._verify_complete_schema(conn) is True
        finally:
            conn.close()

    def test_additive_schema_repair_preserves_all_persisted_data(self, db_path):
        """Finding 49: additive schema repair must NOT drop the table or
        delete persisted rows.  When the table exists but has missing
        columns, _repair_schema_additive adds the missing columns WITHOUT
        destroying existing data.  The previous DROP TABLE + recreate
        approach silently deleted all persisted Project Bindings."""
        conn1 = pb.connect(db_path=db_path)
        try:
            r1 = pb.create_binding(conn1, **valid_kwargs(bound_project_cwd="/tmp/first"))
            r2 = pb.create_binding(
                conn1,
                **valid_kwargs(
                    bound_project_cwd="/tmp/second",
                    github_reference={"owner": "Other", "repo": "Repo"},
                    bmad_skill_dir="/tmp/other/_bmad",
                    provider_name="other-provider",
                    provider_binding_name="other-binding",
                    provider_metadata={"key": "value"},
                ),
            )
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute(
                "ALTER TABLE project_bindings DROP COLUMN provider_metadata"
            )
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True

            b1 = pb.get_binding(conn2, r1["id"])
            assert b1 is not None, "first binding must survive additive repair"
            assert b1.bound_project_cwd == "/tmp/first"
            assert b1.display_name == "Hermes Agent"
            assert b1.profile == "default"

            b2 = pb.get_binding(conn2, r2["id"])
            assert b2 is not None, "second binding must survive additive repair"
            assert b2.bound_project_cwd == "/tmp/second"
            assert b2.github_reference == {"owner": "Other", "repo": "Repo"}
            assert b2.bmad_skill_dir == "/tmp/other/_bmad"
            assert b2.provider_name == "other-provider"
            assert b2.provider_binding_name == "other-binding"

            assert row_count(conn2) == 2
        finally:
            conn2.close()

    def test_additive_repair_adds_missing_columns_preserving_existing_data(self, db_path):
        """Additive repair adds missing columns via add_column_if_missing
        while preserving existing data.  Unlike DROP TABLE + recreate,
        persisted rows survive the repair."""
        conn1 = pb.connect(db_path=db_path)
        try:
            created = pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_bmad_dir")
            conn_alter.execute("ALTER TABLE project_bindings DROP COLUMN bmad_skill_dir")
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            columns = {
                row["name"]
                for row in conn2.execute("PRAGMA table_info(project_bindings)").fetchall()
            }
            assert "bmad_skill_dir" in columns, "missing column should be added by repair"
            assert pb._verify_complete_schema(conn2) is True

            binding = pb.get_binding(conn2, created["id"])
            assert binding is not None, "binding must survive additive repair"
            assert binding.display_name == "Hermes Agent"
            assert binding.bound_project_cwd == valid_kwargs()["bound_project_cwd"]
        finally:
            conn2.close()


@requires_bindings_module
class TestGithubReferenceJsonValidation:
    """Finding 50: github_reference values must be validated for JSON type
    compatibility before persistence, matching the validation discipline
    already applied to provider_metadata. Without this, non-JSON-native
    types (bytes, sets, custom objects) in github_reference values would
    reach json.dumps where the error message is less specific."""

    @pytest.mark.parametrize(
        "bad_ref",
        [
            {"owner": "test", "repo": "ok", "extra": b"bytes_value"},
            {"owner": "test", "repo": "ok", "extra": {1, 2, 3}},
            {"owner": "test", "repo": "ok", "nested": {"deep": object()}},
        ],
        ids=[
            "bytes-in-extra-key",
            "set-in-extra-key",
            "object-in-nested",
        ],
    )
    def test_reject_non_json_native_types_in_github_reference(self, conn, bad_ref):
        """github_reference with non-JSON-native types in extra keys is
        rejected by _require_json_compatible inside _validate_github_reference
        — TypeError, zero rows persisted."""
        with pytest.raises(TypeError):
            pb.create_binding(conn, **valid_kwargs(github_reference=bad_ref))
        assert row_count(conn) == 0

    @pytest.mark.parametrize(
        "bad_ref",
        [
            {"owner": "test", "repo": "ok", "extra": float("inf")},
            {"owner": "test", "repo": "ok", "nested": {"deep": float("nan")}},
        ],
        ids=[
            "inf-in-extra-key",
            "nan-in-nested",
        ],
    )
    def test_reject_non_finite_floats_in_github_reference(self, conn, bad_ref):
        """Non-finite floats in github_reference extra keys are rejected —
        they are not representable in JSON. Owner/repo are checked by
        isinstance(str) first, so non-finite values must be in extra keys
        to exercise the _require_json_compatible path."""
        with pytest.raises(TypeError, match="non-finite float"):
            pb.create_binding(conn, **valid_kwargs(github_reference=bad_ref))
        assert row_count(conn) == 0

    def test_reject_non_string_dict_keys_in_github_reference(self, conn):
        """Finding 50: github_reference with non-string dict keys is rejected
        by _require_json_compatible — json.dumps would silently stringify
        non-string keys (e.g. 1 → "1"), causing lossy round-trips. The
        pre-serialization check catches this with a specific TypeError."""
        bad_ref = {"owner": "test", "repo": "ok", 1: "non-string-key"}
        with pytest.raises(TypeError, match="dict key"):
            pb.create_binding(conn, **valid_kwargs(github_reference=bad_ref))
        assert row_count(conn) == 0

    def test_reject_non_string_dict_keys_in_provider_metadata(self, conn):
        """Finding 50: provider_metadata with non-string dict keys is
        rejected — same lossy stringification risk as github_reference."""
        bad_metadata = {"bindingId": "wpb_123", 42: "non-string-key"}
        with pytest.raises(TypeError, match="dict key"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=bad_metadata,
                ),
            )
        assert row_count(conn) == 0


@requires_bindings_module
class TestAdditiveRepairFixesBrokenIndexes:
    """Finding 52: _repair_schema_additive must fix indexes with wrong
    definitions, not just recreate missing indexes. An index that exists
    by name but has the wrong definition (non-unique, missing WHERE
    predicate, wrong columns) must be dropped and recreated with the
    correct definition during additive repair. DROP INDEX is safe because
    indexes are metadata, not persisted data."""

    def test_repair_fixes_non_unique_index_to_unique(self, db_path):
        """When a unique index is externally replaced with a non-unique
        index of the same name, additive repair must drop the non-unique
        index and recreate it as unique — restoring the uniqueness
        constraint."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn_alter.execute(
                "CREATE INDEX uq_pb_profile_cwd"
                " ON project_bindings(profile, bound_project_cwd)"
            )
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True
            indexes = conn2.execute("PRAGMA index_list(project_bindings)").fetchall()
            index_map = {row["name"]: row for row in indexes}
            assert index_map["uq_pb_profile_cwd"]["unique"] == 1

            conflict = pb.create_binding(conn2, **valid_kwargs())
            assert conflict["conflict"] is True
            assert "bound_project_cwd" in conflict["violations"]
        finally:
            conn2.close()

    def test_repair_fixes_index_missing_where_predicate(self, db_path):
        """When a partial unique index is externally replaced with a
        full unique index (missing the WHERE predicate), additive repair
        must drop and recreate it with the correct WHERE clause —
        restoring partial index semantics."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_github_key")
            conn_alter.execute(
                "CREATE UNIQUE INDEX uq_pb_profile_github_key"
                " ON project_bindings(profile, github_reference_key)"
            )
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True

            sql_row = conn2.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_pb_profile_github_key'"
            ).fetchone()
            assert sql_row and "WHERE" in sql_row["sql"].upper()
        finally:
            conn2.close()

    def test_repair_fixes_index_with_wrong_columns(self, db_path):
        """When a unique index is externally replaced with one covering
        the wrong columns, additive repair must drop and recreate it
        with the correct column composition."""
        conn1 = pb.connect(db_path=db_path)
        try:
            pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn_alter.execute(
                "CREATE UNIQUE INDEX uq_pb_profile_cwd"
                " ON project_bindings(profile)"
            )
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True

            cols = conn2.execute("PRAGMA index_info(uq_pb_profile_cwd)").fetchall()
            actual_cols = tuple(row["name"] for row in cols)
            assert actual_cols == ("profile", "bound_project_cwd")
        finally:
            conn2.close()

    def test_repair_preserves_data_when_fixing_broken_indexes(self, db_path):
        """DROP INDEX + recreate must not affect persisted rows. Two
        bindings created before repair must survive with all fields
        intact after the repair drops and recreates all indexes."""
        conn1 = pb.connect(db_path=db_path)
        try:
            r1 = pb.create_binding(
                conn1,
                **valid_kwargs(
                    bound_project_cwd="/tmp/first",
                    github_reference=None,
                    bmad_skill_dir=None,
                    provider_name=None,
                    provider_binding_name=None,
                    provider_metadata=None,
                ),
            )
            r2 = pb.create_binding(
                conn1,
                **valid_kwargs(
                    bound_project_cwd="/tmp/second",
                    github_reference={"owner": "Other", "repo": "Repo"},
                    bmad_skill_dir="/tmp/other/_bmad",
                    provider_name="other",
                    provider_binding_name="binding",
                    provider_metadata={"key": "value"},
                ),
            )
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn_alter.execute(
                "CREATE INDEX uq_pb_profile_cwd"
                " ON project_bindings(profile, bound_project_cwd)"
            )
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_provider")
            conn_alter.execute(
                "CREATE INDEX uq_pb_profile_provider"
                " ON project_bindings(profile, provider_name)"
            )
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True

            b1 = pb.get_binding(conn2, r1["id"])
            assert b1 is not None
            assert b1.bound_project_cwd == "/tmp/first"
            assert b1.github_reference is None

            b2 = pb.get_binding(conn2, r2["id"])
            assert b2 is not None
            assert b2.bound_project_cwd == "/tmp/second"
            assert b2.github_reference == {"owner": "Other", "repo": "Repo"}
            assert b2.provider_name == "other"
            assert b2.provider_metadata == {"key": "value"}

            assert row_count(conn2) == 2
        finally:
            conn2.close()

    def test_uniqueness_enforced_after_repair_of_broken_indexes(self, db_path):
        """After additive repair fixes broken indexes, uniqueness
        constraints must be enforced — attempting to create a binding
        that collides on a repaired dimension must return a conflict."""
        conn1 = pb.connect(db_path=db_path)
        try:
            original = pb.create_binding(conn1, **valid_kwargs())
        finally:
            conn1.close()

        conn_alter = sqlite3.connect(str(db_path))
        try:
            conn_alter.execute("DROP INDEX IF EXISTS uq_pb_profile_cwd")
            conn_alter.execute(
                "CREATE INDEX uq_pb_profile_cwd"
                " ON project_bindings(profile, bound_project_cwd)"
            )
            conn_alter.commit()
        finally:
            conn_alter.close()

        conn2 = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn2) is True

            conflict = pb.create_binding(conn2, **valid_kwargs())
            assert conflict["conflict"] is True
            assert "bound_project_cwd" in conflict["violations"]
            assert conflict["violations"]["bound_project_cwd"] == original["id"]
            assert row_count(conn2) == 1
        finally:
            conn2.close()

    def test_index_repair_rolls_back_if_recreate_fails(self, db_path):
        """Index repair must not leave previously-valid indexes dropped when
        one recreate statement fails midway through the repair loop."""
        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True
            before = {
                row["name"]
                for row in conn.execute("PRAGMA index_list(project_bindings)").fetchall()
            }
            assert pb._EXPECTED_UNIQUE_INDEXES.issubset(before)

            class FailingIndexRepairConnection:
                def __init__(self, wrapped):
                    self._wrapped = wrapped

                def execute(self, sql, *args):
                    normalized = " ".join(sql.split())
                    if normalized.startswith(
                        "CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_github_key"
                    ):
                        raise sqlite3.OperationalError("simulated index recreate failure")
                    return self._wrapped.execute(sql, *args)

                def executescript(self, sql):
                    return self._wrapped.executescript(sql)

            with pytest.raises(sqlite3.OperationalError, match="simulated"):
                pb._repair_schema_additive(FailingIndexRepairConnection(conn))

            after = {
                row["name"]
                for row in conn.execute("PRAGMA index_list(project_bindings)").fetchall()
            }
            assert after == before
            assert pb._verify_complete_schema(conn) is True
        finally:
            conn.close()


@requires_bindings_module
class TestProviderIdentityEdgeCases:
    """Finding 53: Provider Controller Identity and JSON validation must
    reject all forms of lossy, contradictory, or ambiguous identity data."""

    def test_reject_provider_name_with_embedded_null(self, conn):
        """provider_name containing null bytes is rejected — null bytes
        cause silent truncation in SQLite and C-level string operations."""
        with pytest.raises(ValueError):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="arch\x00on",
                    provider_binding_name="default",
                ),
            )
        assert row_count(conn) == 0

    def test_reject_provider_binding_name_with_embedded_null(self, conn):
        """provider_binding_name containing null bytes is rejected."""
        with pytest.raises(ValueError):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="def\x00ault",
                ),
            )
        assert row_count(conn) == 0

    def test_provider_identity_with_unicode_survives_roundtrip(self, conn):
        """Provider identity with non-ASCII characters survives a full
        create+read round-trip without loss."""
        result = pb.create_binding(
            conn,
            **valid_kwargs(
                provider_name="архонт",
                provider_binding_name="绑定",
            ),
        )
        binding = pb.get_binding(conn, result["id"])
        assert binding.provider_name == "архонт"
        assert binding.provider_binding_name == "绑定"

    def test_reject_provider_metadata_with_nested_non_string_keys(self, conn):
        """provider_metadata with non-string keys in nested dicts is
        rejected — json.dumps would silently stringify them."""
        bad_metadata = {"nested": {42: "value"}}
        with pytest.raises(TypeError, match="dict key"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=bad_metadata,
                ),
            )
        assert row_count(conn) == 0

    def test_reject_github_reference_with_nested_non_string_keys(self, conn):
        """github_reference with non-string keys in nested dicts is
        rejected — same lossy stringification risk."""
        bad_ref = {"owner": "test", "repo": "ok", "extra": {42: "value"}}
        with pytest.raises(TypeError, match="dict key"):
            pb.create_binding(conn, **valid_kwargs(github_reference=bad_ref))
        assert row_count(conn) == 0


@requires_bindings_module
class TestPrimaryKeyVerification:
    """Finding 315 (re-review of Finding 49): _verify_complete_schema must
    verify the PRIMARY KEY constraint on the id column. Without this check,
    an externally recreated table lacking PRIMARY KEY would pass all other
    schema checks but allow duplicate binding ids."""

    def test_verify_complete_schema_detects_missing_primary_key(self, db_path):
        """_verify_complete_schema returns False when the table exists with
        all expected columns and indexes but lacks PRIMARY KEY on id."""
        if not hasattr(pb, "_verify_complete_schema"):
            pytest.skip("pb._verify_complete_schema not present")

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True

            conn.execute("DROP TABLE project_bindings")
            conn.executescript("""
                CREATE TABLE project_bindings (
                    id                      TEXT,
                    profile                 TEXT NOT NULL,
                    display_name            TEXT NOT NULL,
                    bound_project_cwd       TEXT NOT NULL,
                    github_reference        TEXT,
                    github_reference_key    TEXT,
                    bmad_skill_dir          TEXT,
                    provider_name           TEXT,
                    provider_binding_name   TEXT,
                    provider_metadata       TEXT,
                    created_at              INTEGER NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_cwd
                    ON project_bindings(profile, bound_project_cwd);
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_github_key
                    ON project_bindings(profile, github_reference_key)
                    WHERE github_reference_key IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_bmad_dir
                    ON project_bindings(profile, bmad_skill_dir)
                    WHERE bmad_skill_dir IS NOT NULL;
                CREATE UNIQUE INDEX IF NOT EXISTS uq_pb_profile_provider
                    ON project_bindings(profile, provider_name, provider_binding_name)
                    WHERE provider_name IS NOT NULL AND provider_binding_name IS NOT NULL;
            """)
            assert pb._verify_complete_schema(conn) is False
        finally:
            conn.close()


@requires_bindings_module
class TestProviderIdentityNullStorageAtDbLevel:
    """Finding 316 (re-review of Finding 50): tests must prove at the DB
    level that blank provider identity is stored as SQL NULL, not empty
    string. This matters because the partial unique index WHERE clause
    only excludes NULL — empty strings would trigger the index and cause
    phantom collisions between bindings that should have no provider
    identity."""

    def test_blank_provider_identity_stored_as_null_not_empty_string(self, conn):
        """Whitespace-only provider_name/provider_binding_name are stored as
        SQL NULL in the database, not empty strings. This is critical because
        the partial unique index (WHERE provider_name IS NOT NULL AND
        provider_binding_name IS NOT NULL) only excludes NULL values — empty
        strings would trigger the index and cause phantom collisions."""
        result = pb.create_binding(
            conn,
            **valid_kwargs(
                provider_name="   ",
                provider_binding_name="   ",
                provider_metadata=None,
            ),
        )
        assert result["conflict"] is False

        row = get_row(conn, result["id"])
        assert row["provider_name"] is None, (
            "blank provider_name must be stored as SQL NULL, not empty string"
        )
        assert row["provider_binding_name"] is None, (
            "blank provider_binding_name must be stored as SQL NULL, not empty string"
        )

        binding = pb.get_binding(conn, result["id"])
        assert binding.provider_name is None
        assert binding.provider_binding_name is None

    def test_null_provider_identity_does_not_trigger_partial_unique_index(
        self, conn
    ):
        """Two bindings with NULL provider identity (from blank coercion)
        do not collide on the provider dimension because the partial unique
        index excludes NULL values. This proves the NULL storage is correct
        at the constraint level, not just the Python level."""
        _minimal = dict(
            github_reference=None,
            bmad_skill_dir=None,
        )
        first = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/null-provider-a",
                provider_name="",
                provider_binding_name="",
                provider_metadata=None,
                **_minimal,
            ),
        )
        second = pb.create_binding(
            conn,
            **valid_kwargs(
                bound_project_cwd="/tmp/null-provider-b",
                provider_name="",
                provider_binding_name="",
                provider_metadata=None,
                **_minimal,
            ),
        )
        assert first["conflict"] is False
        assert second["conflict"] is False
        assert row_count(conn) == 2

        for binding_id in (first["id"], second["id"]):
            row = get_row(conn, binding_id)
            assert row["provider_name"] is None
            assert row["provider_binding_name"] is None


@requires_bindings_module
class TestColdPathSchemaVerification:
    """Finding 317: _init_connection_with_retry must verify schema
    completeness after _ensure_schema. CREATE TABLE IF NOT EXISTS silently
    skips when a pre-existing table exists — even if that table has wrong
    columns, missing PRIMARY KEY, or missing indexes. Without post-init
    verification, a DB file with a broken pre-existing table would pass
    initialization but produce confusing errors on first use."""

    def test_cold_init_repair_fixes_preexisting_broken_table(self, db_path):
        """When connect() is called against a DB file with a pre-existing
        broken table (missing column), the cold init path must detect the
        broken schema via _verify_complete_schema and repair it additively
        — the resulting connection must have a complete schema."""
        conn_broken = sqlite3.connect(str(db_path))
        try:
            conn_broken.executescript("""
                CREATE TABLE project_bindings (
                    id                      TEXT PRIMARY KEY,
                    profile                 TEXT NOT NULL,
                    display_name            TEXT NOT NULL,
                    bound_project_cwd       TEXT NOT NULL,
                    created_at              INTEGER NOT NULL
                );
            """)
        finally:
            conn_broken.close()

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True
            result = pb.create_binding(conn, **valid_kwargs())
            assert result["conflict"] is False
            binding = pb.get_binding(conn, result["id"])
            assert binding is not None
            assert binding.display_name == "Hermes Agent"
        finally:
            conn.close()

    def test_cold_init_repair_fixes_preexisting_missing_indexes(self, db_path):
        """When connect() is called against a DB file with a pre-existing
        table that has the right columns but missing indexes, the cold init
        path must detect and repair the missing indexes."""
        conn_broken = sqlite3.connect(str(db_path))
        try:
            conn_broken.executescript("""
                CREATE TABLE project_bindings (
                    id                      TEXT PRIMARY KEY,
                    profile                 TEXT NOT NULL,
                    display_name            TEXT NOT NULL,
                    bound_project_cwd       TEXT NOT NULL,
                    github_reference        TEXT,
                    github_reference_key    TEXT,
                    bmad_skill_dir          TEXT,
                    provider_name           TEXT,
                    provider_binding_name   TEXT,
                    provider_metadata       TEXT,
                    created_at              INTEGER NOT NULL
                );
            """)
        finally:
            conn_broken.close()

        conn = pb.connect(db_path=db_path)
        try:
            assert pb._verify_complete_schema(conn) is True
            indexes = conn.execute("PRAGMA index_list(project_bindings)").fetchall()
            index_names = {row["name"] for row in indexes}
            assert "uq_pb_profile_cwd" in index_names
            assert "uq_pb_profile_github_key" in index_names
            assert "uq_pb_profile_bmad_dir" in index_names
            assert "uq_pb_profile_provider" in index_names
        finally:
            conn.close()

    def test_cold_init_raises_when_repair_cannot_restore_schema(self, db_path):
        """When the cold init path cannot repair the schema (e.g. the DB
        file is corrupt), it raises RuntimeError instead of returning a
        connection with a broken schema."""
        conn_broken = sqlite3.connect(str(db_path))
        try:
            conn_broken.executescript("""
                CREATE TABLE project_bindings (
                    id                      TEXT PRIMARY KEY,
                    profile                 TEXT NOT NULL,
                    display_name            TEXT NOT NULL,
                    bound_project_cwd       TEXT NOT NULL,
                    created_at              INTEGER NOT NULL
                );
            """)
            conn_broken.execute(
                "ALTER TABLE project_bindings DROP COLUMN display_name"
            )
            conn_broken.commit()
        finally:
            conn_broken.close()

        original_repair = pb._repair_schema_additive
        def broken_repair(conn):
            pass
        pb._repair_schema_additive = broken_repair
        try:
            with pytest.raises(RuntimeError, match="verification still failed"):
                pb.connect(db_path=db_path)
        finally:
            pb._repair_schema_additive = original_repair
            pb._INITIALIZED_PATHS.discard(str(db_path.resolve()))


@requires_bindings_module
class TestNullByteRejectionInStringFields:
    """Finding 318: null bytes must be rejected in all string fields that
    reach SQLite — display_name (via _require_nonblank_str), github
    owner/repo (via _validate_github_reference), and JSON string values
    (via _require_json_compatible). Null bytes cause silent truncation
    in SQLite and C-level string operations."""

    def test_reject_display_name_with_embedded_null(self, conn):
        """display_name containing null bytes is rejected by
        _require_nonblank_str — null bytes cause silent truncation in
        SQLite."""
        with pytest.raises(ValueError, match="null bytes"):
            pb.create_binding(conn, **valid_kwargs(display_name="test\x00name"))
        assert row_count(conn) == 0

    def test_reject_github_owner_with_embedded_null(self, conn):
        """github_reference owner containing null bytes is rejected by
        _validate_github_reference — null bytes cause silent truncation."""
        with pytest.raises(ValueError, match="null bytes"):
            pb.create_binding(
                conn,
                **valid_kwargs(github_reference={"owner": "test\x00owner", "repo": "ok"}),
            )
        assert row_count(conn) == 0

    def test_reject_github_repo_with_embedded_null(self, conn):
        """github_reference repo containing null bytes is rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            pb.create_binding(
                conn,
                **valid_kwargs(github_reference={"owner": "ok", "repo": "test\x00repo"}),
            )
        assert row_count(conn) == 0

    def test_reject_null_byte_in_provider_metadata_string_value(self, conn):
        """provider_metadata with null bytes in string values is rejected
        by _require_json_compatible — catches null bytes in nested JSON
        string values before they reach SQLite."""
        bad_metadata = {"bindingId": "wpb_\x00_injected"}
        with pytest.raises(TypeError, match="null byte"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=bad_metadata,
                ),
            )
        assert row_count(conn) == 0

    def test_reject_null_byte_in_github_reference_extra_string_value(self, conn):
        """github_reference with null bytes in extra string values is
        rejected by _require_json_compatible."""
        bad_ref = {"owner": "test", "repo": "ok", "extra": "value\x00injected"}
        with pytest.raises(TypeError, match="null byte"):
            pb.create_binding(conn, **valid_kwargs(github_reference=bad_ref))
        assert row_count(conn) == 0

    def test_reject_null_byte_in_nested_json_string_value(self, conn):
        """provider_metadata with null bytes in nested string values is
        rejected — the recursive check catches null bytes at any depth."""
        bad_metadata = {"nested": {"deep": "value\x00injected"}}
        with pytest.raises(TypeError, match="null byte"):
            pb.create_binding(
                conn,
                **valid_kwargs(
                    provider_name="archon",
                    provider_binding_name="default",
                    provider_metadata=bad_metadata,
                ),
            )
        assert row_count(conn) == 0


# =============================================================================
# Story 2.1b: Validate Project Binding Safety And Conflicts
#
# TDD RED PHASE: hermes_project_work.bindings does not yet define
# `_check_cwd_safety`, `_check_bmad_reference_safety`,
# `_check_github_reference_safety`, `_check_provider_metadata_safety`,
# `_CONFLICT_CATEGORY_BY_DIMENSION`, `preview_binding_conflicts()`, or
# `validate_binding()` (Story 2.1b, Tasks 1-5). Unlike the Story 2.1a suite
# above, `hermes_project_work.bindings` itself already imports cleanly
# (2.1a is done) — every test below is an EXECUTABLE red test, not a
# skip-gated scaffold: each calls the not-yet-implemented symbol directly
# and is expected to fail with AttributeError until its Task lands. There is
# no module-level skip guard here because the missing seam is "attribute
# missing from an existing module", not "module missing" — activate a test
# class by implementing the Task it is commented against.
#
# The exception is `TestScopeRegressionGuards` and the
# `test_no_*`/`test_conflict_categories_map_exact_dimension_strings`-style
# static checks: those assert the CURRENT absence of scope-creep surface
# and must stay green both before and after implementation — they are
# regression guards, not red tests.
#
# Traceability: each test is tagged with its
# `_bmad-output/test-artifacts/test-design-epic-2.1b.md` scenario ID.
# =============================================================================


def _make_git_repo(tmp_path: Path, name: str = "repo") -> Path:
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)
    (repo / ".git").mkdir(exist_ok=True)
    return repo


def _make_plain_dir(tmp_path: Path, name: str) -> Path:
    d = tmp_path / name
    d.mkdir(parents=True, exist_ok=True)
    return d


def real_binding_kwargs(
    tmp_path: Path,
    *,
    repo_name: str = "repo",
    bmad_name: str = "_bmad",
    **overrides: Any,
) -> dict:
    """Like ``valid_kwargs()`` but with a real, tmp_path-backed
    ``bound_project_cwd`` (containing ``.git``) and ``bmad_skill_dir``, for
    ``validate_binding()``/``preview_binding_conflicts()`` tests that
    exercise real filesystem checks rather than 2.1a's fake ``/tmp`` paths.
    Override any field (including ``bound_project_cwd``/``bmad_skill_dir``
    themselves, to point at a path that was never created) via kwargs.
    """
    repo = _make_git_repo(tmp_path, repo_name)
    bmad_dir = _make_plain_dir(tmp_path, bmad_name)
    base = dict(
        profile="default",
        display_name="Hermes Agent",
        bound_project_cwd=str(repo),
        github_reference={"owner": "NousResearch", "repo": "hermes-agent"},
        bmad_skill_dir=str(bmad_dir),
        provider_name="archon",
        provider_binding_name="workflow-engine-primary",
        provider_metadata={"bindingId": "wpb_archon_workflow_engine_primary"},
    )
    base.update(overrides)
    return base


def set_raw_column(conn: sqlite3.Connection, binding_id: str, column: str, value) -> None:
    """Bypass ``create_binding()``'s validation to inject malformed
    persisted data directly, simulating a row written by some future path
    that doesn't reuse 2.1a's fail-fast validators (per this story's Dev
    Notes on non-raising vs. raising validation)."""
    conn.execute(
        f"UPDATE project_bindings SET {column} = ? WHERE id = ?",
        (value, binding_id),
    )
    conn.commit()


class TestCwdSafetyValidation:
    """Unit tests for `_check_cwd_safety()` (Story 2.1b, Task 1)."""

    def test_missing_cwd_reports_does_not_exist(self, tmp_path):
        """2.1B-UNIT-001 (P0, AC1, R-001)."""
        missing = tmp_path / "does-not-exist"
        assert pb._check_cwd_safety(str(missing)) == {
            "valid": False,
            "reason": "cwd_does_not_exist",
        }

    def test_file_not_directory_reports_not_a_directory(self, tmp_path):
        """2.1B-UNIT-002 (P0, AC1, R-001)."""
        file_path = tmp_path / "a-file"
        file_path.write_text("x", encoding="utf-8")
        assert pb._check_cwd_safety(str(file_path)) == {
            "valid": False,
            "reason": "cwd_is_not_a_directory",
        }

    def test_filesystem_root_reports_is_filesystem_root(self):
        """2.1B-UNIT-003 (P0, AC1, R-001/R-002): tmp_path fixtures cannot
        naturally produce a real filesystem root, so this exercises the
        real POSIX root directly, per Task 6's own guidance."""
        assert pb._check_cwd_safety(os.path.abspath(os.sep)) == {
            "valid": False,
            "reason": "cwd_is_filesystem_root",
        }

    def test_exact_hermes_home_reports_within_hermes_home(self, tmp_path, monkeypatch):
        """2.1B-UNIT-004 (P0, AC1, R-001/R-002): exact Hermes-home match."""
        fake_home = tmp_path / "hermes-home"
        fake_home.mkdir()
        monkeypatch.setattr(pb, "get_hermes_home", lambda: fake_home)
        assert pb._check_cwd_safety(str(fake_home)) == {
            "valid": False,
            "reason": "cwd_is_within_hermes_home",
        }

    def test_nested_hermes_home_reports_within_hermes_home(self, tmp_path, monkeypatch):
        """2.1B-UNIT-004 (P0, AC1, R-001/R-002): nested-under Hermes home."""
        fake_home = tmp_path / "hermes-home"
        nested = fake_home / "profiles" / "default"
        nested.mkdir(parents=True)
        monkeypatch.setattr(pb, "get_hermes_home", lambda: fake_home)
        assert pb._check_cwd_safety(str(nested)) == {
            "valid": False,
            "reason": "cwd_is_within_hermes_home",
        }

    def test_directory_without_git_reports_not_a_git_repository(self, tmp_path):
        """2.1B-UNIT-005 (P0, AC3, R-001/R-003)."""
        plain_dir = _make_plain_dir(tmp_path, "no-git-here")
        assert pb._check_cwd_safety(str(plain_dir)) == {
            "valid": False,
            "reason": "cwd_is_not_a_git_repository",
        }

    def test_directory_with_git_is_valid(self, tmp_path):
        """2.1B-UNIT-006 (P1, AC6, R-001)."""
        repo = _make_git_repo(tmp_path)
        assert pb._check_cwd_safety(str(repo)) == {"valid": True, "reason": None}

    def test_existence_check_gates_hermes_home_check(self, tmp_path, monkeypatch):
        """Reviewer concern (R-001/R-002): a check on a nonexistent path is
        meaningless, so existence must be checked before the Hermes-home
        denylist — even for a path that WOULD be nested under Hermes home
        if it existed."""
        fake_home = tmp_path / "hermes-home"
        fake_home.mkdir()
        monkeypatch.setattr(pb, "get_hermes_home", lambda: fake_home)
        missing_nested = fake_home / "missing"
        assert pb._check_cwd_safety(str(missing_nested)) == {
            "valid": False,
            "reason": "cwd_does_not_exist",
        }

    def test_directory_check_gates_git_check(self, tmp_path):
        """Reviewer concern (R-001/R-003): a file (not a directory) must be
        flagged as not-a-directory, never misreported as not-a-git-repo."""
        file_path = tmp_path / "a-file"
        file_path.write_text("x", encoding="utf-8")
        assert pb._check_cwd_safety(str(file_path))["reason"] == "cwd_is_not_a_directory"

    def test_hermes_home_check_gates_git_check(self, tmp_path, monkeypatch):
        """Reviewer concern (R-001/R-002/R-003): a directory nested under
        Hermes home with no `.git` subdirectory must report the Hermes-home
        denylist reason, not the git-repository reason — proving check
        order 4 runs before check order 5."""
        fake_home = tmp_path / "hermes-home"
        nested = fake_home / "nested"
        nested.mkdir(parents=True)
        monkeypatch.setattr(pb, "get_hermes_home", lambda: fake_home)
        assert pb._check_cwd_safety(str(nested)) == {
            "valid": False,
            "reason": "cwd_is_within_hermes_home",
        }


class TestBmadReferenceSafety:
    """Unit tests for `_check_bmad_reference_safety()` (Story 2.1b, Task 2)."""

    def test_none_input_returns_none(self):
        """2.1B-UNIT-007 (P1, AC4, R-004)."""
        assert pb._check_bmad_reference_safety(None) is None

    def test_missing_directory_reports_invalid(self, tmp_path):
        """2.1B-UNIT-008 (P1, AC4, R-004)."""
        missing = tmp_path / "no-such-bmad-dir"
        assert pb._check_bmad_reference_safety(str(missing)) == {
            "valid": False,
            "reason": "bmad_skill_dir_does_not_exist",
        }

    def test_file_not_directory_reports_invalid(self, tmp_path):
        """2.1B-UNIT-009 (P1, AC4, R-004)."""
        file_path = tmp_path / "bmad-as-file"
        file_path.write_text("x", encoding="utf-8")
        assert pb._check_bmad_reference_safety(str(file_path)) == {
            "valid": False,
            "reason": "bmad_skill_dir_is_not_a_directory",
        }

    def test_existing_directory_returns_valid(self, tmp_path):
        """2.1B-UNIT-010 (P1, AC4/AC6, R-004)."""
        bmad_dir = _make_plain_dir(tmp_path, "_bmad")
        assert pb._check_bmad_reference_safety(str(bmad_dir)) == {
            "valid": True,
            "reason": None,
        }


class TestGithubAndProviderMetadataSafety:
    """Unit tests for `_check_github_reference_safety()` and
    `_check_provider_metadata_safety()` (Story 2.1b, Task 3): non-raising
    wrappers around 2.1a's fail-fast `_validate_github_reference()` /
    `_validate_provider_identity()`."""

    def test_github_reference_none_returns_valid(self):
        """2.1B-UNIT-011 (P1, AC5, R-011)."""
        assert pb._check_github_reference_safety(None) == {"valid": True, "reason": None}

    def test_github_reference_valid_dict_returns_valid(self):
        """2.1B-UNIT-011 (P1, AC5, R-011)."""
        ref = {"owner": "NousResearch", "repo": "hermes-agent"}
        assert pb._check_github_reference_safety(ref) == {"valid": True, "reason": None}

    @pytest.mark.parametrize(
        "malformed",
        [
            {"owner": "NousResearch"},
            "NousResearch/hermes-agent",
            {"owner": "", "repo": "hermes-agent"},
        ],
        ids=["missing-repo", "bare-string", "blank-owner"],
    )
    def test_github_reference_converts_raised_errors_to_invalid(self, malformed):
        """2.1B-UNIT-012 (P1, AC5, R-005/R-011): shapes that make
        `_validate_github_reference()` raise must come back as a
        structured `{"valid": False, "reason": <str>}`, never an escaped
        exception."""
        result = pb._check_github_reference_safety(malformed)
        assert result["valid"] is False
        assert isinstance(result["reason"], str) and result["reason"]

    def test_github_reference_safety_wraps_not_reimplements_validator(self, monkeypatch):
        """R-011 (P2 reviewer concern, tracked here for completeness):
        `_check_github_reference_safety` must call the existing
        `_validate_github_reference()`, not duplicate its logic — proven
        with a call-counting spy."""
        calls = []
        real = pb._validate_github_reference

        def _spy(ref):
            calls.append(ref)
            return real(ref)

        monkeypatch.setattr(pb, "_validate_github_reference", _spy)
        ref = {"owner": "NousResearch", "repo": "hermes-agent"}
        assert pb._check_github_reference_safety(ref) == {"valid": True, "reason": None}
        assert calls == [ref]

    def test_provider_metadata_safety_absent_identity_returns_valid(self):
        """2.1B-UNIT-013 (P1, AC5, R-011)."""
        assert pb._check_provider_metadata_safety(None, None, None) == {
            "valid": True,
            "reason": None,
        }

    def test_provider_metadata_safety_complete_identity_returns_valid(self):
        """2.1B-UNIT-013 (P1, AC5, R-011)."""
        result = pb._check_provider_metadata_safety(
            "archon", "workflow-engine-primary", {"bindingId": "wpb_x"}
        )
        assert result == {"valid": True, "reason": None}

    @pytest.mark.parametrize(
        "provider_name,provider_binding_name,provider_metadata",
        [
            ("archon", None, None),
            (None, "workflow-engine-primary", None),
            (None, None, {"bindingId": "wpb_x"}),
        ],
        ids=[
            "one-sided-name-only",
            "one-sided-binding-name-only",
            "metadata-without-identity",
        ],
    )
    def test_provider_metadata_safety_converts_raised_errors_to_invalid(
        self, provider_name, provider_binding_name, provider_metadata
    ):
        """2.1B-UNIT-014 (P1, AC5, R-005/R-011): one-sided Controller
        Identity and metadata-without-identity must come back as a
        structured invalid result, never an escaped exception."""
        result = pb._check_provider_metadata_safety(
            provider_name, provider_binding_name, provider_metadata
        )
        assert result["valid"] is False
        assert isinstance(result["reason"], str) and result["reason"]

    def test_provider_metadata_safety_non_dict_metadata_returns_invalid(self):
        """2.1B-UNIT-014 (P1, AC5, R-005/R-011): non-dict provider_metadata
        must also be converted, not just identity-shape failures."""
        result = pb._check_provider_metadata_safety(
            "archon", "workflow-engine-primary", ["not", "a", "dict"]
        )
        assert result["valid"] is False
        assert isinstance(result["reason"], str) and result["reason"]

    def test_provider_metadata_safety_wraps_not_reimplements_validator(self, monkeypatch):
        """R-011 (P2 reviewer concern): `_check_provider_metadata_safety`
        must call the existing `_validate_provider_identity()`, not
        duplicate it."""
        calls = []
        real = pb._validate_provider_identity

        def _spy(provider_name, provider_binding_name, provider_metadata=None):
            calls.append((provider_name, provider_binding_name, provider_metadata))
            return real(provider_name, provider_binding_name, provider_metadata)

        monkeypatch.setattr(pb, "_validate_provider_identity", _spy)
        result = pb._check_provider_metadata_safety(
            "archon", "engine", {"bindingId": "wpb_x"}
        )
        assert result == {"valid": True, "reason": None}
        assert calls == [("archon", "engine", {"bindingId": "wpb_x"})]


class TestPreviewBindingConflicts:
    """Integration tests for `preview_binding_conflicts()` (Story 2.1b,
    Task 4). Read-only: must never create a row. Real SQLite + tmp_path
    filesystem, no mocks."""

    def test_cwd_conflict_returns_category_and_existing_id(self, conn, tmp_path):
        """2.1B-INT-008 (P0, AC2/AC7, R-006)."""
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        assert existing["conflict"] is False
        before = row_count(conn)

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "existing"),
            github_reference={"owner": "Other", "repo": "other-repo"},
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
        )
        assert result == [{"category": "cwd_conflict", "conflicting_binding_id": existing["id"]}]
        assert row_count(conn) == before

    def test_github_conflict_returns_category_and_existing_id(self, conn, tmp_path):
        """2.1B-INT-009 (P0, AC2/AC7, R-006/R-014)."""
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        before = row_count(conn)

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "candidate"),
            github_reference={"owner": "nousresearch", "repo": "HERMES-AGENT"},
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
        )
        assert result == [
            {"category": "github_reference_conflict", "conflicting_binding_id": existing["id"]}
        ]
        assert row_count(conn) == before

    def test_bmad_conflict_returns_category_and_existing_id(self, conn, tmp_path):
        """2.1B-INT-010 (P0, AC2/AC7, R-006)."""
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        before = row_count(conn)

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "candidate2"),
            github_reference=None,
            bmad_skill_dir=str(tmp_path / "_bmad"),
            provider_name=None,
            provider_binding_name=None,
        )
        assert result == [
            {"category": "bmad_mount_conflict", "conflicting_binding_id": existing["id"]}
        ]
        assert row_count(conn) == before

    def test_provider_conflict_returns_category_and_existing_id(self, conn, tmp_path):
        """2.1B-INT-011 (P0, AC2/AC7, R-006)."""
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        before = row_count(conn)

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "candidate3"),
            github_reference=None,
            bmad_skill_dir=None,
            provider_name="archon",
            provider_binding_name="workflow-engine-primary",
        )
        assert result == [
            {"category": "provider_identity_conflict", "conflicting_binding_id": existing["id"]}
        ]
        assert row_count(conn) == before

    def test_all_four_dimensions_conflict_reports_all_categories(self, conn, tmp_path):
        """2.1B-INT-012 (P0, AC2/AC7, R-006)."""
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        before = row_count(conn)

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "existing"),
            github_reference={"owner": "NousResearch", "repo": "hermes-agent"},
            bmad_skill_dir=str(tmp_path / "_bmad"),
            provider_name="archon",
            provider_binding_name="workflow-engine-primary",
        )
        assert {c["category"] for c in result} == {
            "cwd_conflict",
            "github_reference_conflict",
            "bmad_mount_conflict",
            "provider_identity_conflict",
        }
        assert all(c["conflicting_binding_id"] == existing["id"] for c in result)
        assert row_count(conn) == before

    def test_non_conflicting_candidate_returns_empty_list(self, conn, tmp_path):
        """2.1B-INT-021 (P1, AC7, R-006)."""
        pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        before = row_count(conn)

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "unrelated"),
            github_reference={"owner": "Someone", "repo": "else"},
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
        )
        assert result == []
        assert row_count(conn) == before

    def test_preview_normalizes_candidate_like_create_binding(self, conn, tmp_path):
        """2.1B-INT-022 (P1, AC7, R-014): a trailing-slash cwd and a
        case/key-order-varied GitHub reference must canonicalize exactly
        like `create_binding()` does, and still be recognized as
        conflicts."""
        pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path,
                repo_name="existing",
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
        )

        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "existing") + "/",
            github_reference={"repo": "HERMES-AGENT", "owner": "nousresearch"},
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
        )
        categories = {c["category"] for c in result}
        assert "cwd_conflict" in categories
        assert "github_reference_conflict" in categories

    def test_invalid_provider_candidate_raises_before_sql(self, conn, tmp_path):
        """2.1B-INT-023 (P1, AC7, R-010/R-014): a one-sided provider
        identity candidate must raise the same way `create_binding()`
        does, before any SQL runs — preview reuses `create_binding()`'s
        pre-mutation validators rather than silently passing malformed
        candidates through."""
        before = row_count(conn)
        with pytest.raises(ValueError):
            pb.preview_binding_conflicts(
                conn,
                profile="default",
                bound_project_cwd=str(tmp_path / "candidate"),
                provider_name="archon",
                provider_binding_name=None,
            )
        assert row_count(conn) == before

    def test_profile_none_resolves_active_profile(self, conn, tmp_path, monkeypatch):
        """2.1B-INT-024 (P1, AC2/AC7, R-014): `profile=None` resolves
        through the same `_resolve_profile()`/`get_active_profile_name()`
        path `create_binding()` uses, and only reports same-profile
        conflicts."""
        import hermes_cli.profiles as profiles_mod

        monkeypatch.setattr(profiles_mod, "get_active_profile_name", lambda: "default")
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))

        result = pb.preview_binding_conflicts(
            conn,
            profile=None,
            bound_project_cwd=str(tmp_path / "existing"),
            github_reference=None,
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
        )
        assert result == [{"category": "cwd_conflict", "conflicting_binding_id": existing["id"]}]

    def test_same_values_different_profile_no_conflict(self, conn, tmp_path):
        """2.1B-INT-025 (P1, AC2/AC7, R-014): uniqueness (and conflict
        detection) is profile-scoped, not global."""
        pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, repo_name="existing", profile="alpha")
        )

        result = pb.preview_binding_conflicts(
            conn,
            profile="beta",
            bound_project_cwd=str(tmp_path / "existing"),
            github_reference={"owner": "NousResearch", "repo": "hermes-agent"},
            bmad_skill_dir=str(tmp_path / "_bmad"),
            provider_name="archon",
            provider_binding_name="workflow-engine-primary",
        )
        assert result == []

    def test_repeated_preview_is_idempotent_and_creates_no_row(self, conn, tmp_path):
        """2.1B-INT-026 (P1, AC7, R-006): calling preview twice with the
        same candidate returns the same conflicts and never creates a
        row."""
        existing = pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="existing"))
        before = row_count(conn)

        candidate = dict(
            profile="default",
            bound_project_cwd=str(tmp_path / "existing"),
            github_reference=None,
            bmad_skill_dir=None,
            provider_name=None,
            provider_binding_name=None,
        )
        first = pb.preview_binding_conflicts(conn, **candidate)
        second = pb.preview_binding_conflicts(conn, **candidate)
        assert (
            first
            == second
            == [{"category": "cwd_conflict", "conflicting_binding_id": existing["id"]}]
        )
        assert row_count(conn) == before


class TestValidateBinding:
    """Integration tests for `validate_binding()` (Story 2.1b, Task 5) —
    the unified re-validation entrypoint. Real SQLite + tmp_path
    filesystem, no mocks, per this project's Testing Rules."""

    def test_fully_valid_binding_is_safe_with_no_diagnostics_or_conflicts(self, conn, tmp_path):
        """2.1B-INT-003 (P0, AC6, R-009)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        result = pb.validate_binding(conn, created["id"])
        assert result["binding_id"] == created["id"]
        assert result["safe"] is True
        assert result["validation_state"] == "valid"
        assert result["diagnostics"] == []
        assert result["conflicts"] == []

    def test_cwd_that_never_existed_returns_invalid_cwd_diagnostic(self, conn, tmp_path):
        """2.1B-INT-001 (P0, AC1, R-001/R-013): `create_binding()` does not
        check cwd existence, so a binding can be persisted with a
        `bound_project_cwd` that never existed on disk."""
        never_existed = str(tmp_path / "never-existed")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bound_project_cwd=never_existed)
        )
        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_cwd"
        assert "invalid_cwd" in {d["category"] for d in result["diagnostics"]}

    def test_existing_non_git_cwd_flagged_not_a_git_repository(self, conn, tmp_path):
        """2.1B-INT-002 (P0, AC3, R-001/R-003)."""
        non_git_dir = _make_plain_dir(tmp_path, "not-a-repo")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bound_project_cwd=str(non_git_dir))
        )
        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["cwd_check"]["reason"] == "cwd_is_not_a_git_repository"

    def test_missing_bmad_dir_returns_invalid_bmad_reference_diagnostic(self, conn, tmp_path):
        """2.1B-INT-018 (P1, AC4, R-004)."""
        missing_bmad = str(tmp_path / "missing-bmad")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bmad_skill_dir=missing_bmad)
        )
        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert "invalid_bmad_reference" in {d["category"] for d in result["diagnostics"]}

    def test_existing_bmad_dir_remains_safe(self, conn, tmp_path):
        """2.1B-INT-019 (P1, AC4/AC6, R-004)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        result = pb.validate_binding(conn, created["id"])
        assert result["bmad_reference_check"] == {"valid": True, "reason": None}
        assert result["safe"] is True

    def test_malformed_github_reference_json_returns_diagnostic_no_exception(self, conn, tmp_path):
        """2.1B-INT-004 (P0, AC5, R-005)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "github_reference", "{not valid json")

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_github_reference"
        assert "invalid_github_reference" in {d["category"] for d in result["diagnostics"]}

    def test_github_reference_non_dict_json_returns_diagnostic_no_exception(self, conn, tmp_path):
        """2.1B-INT-005 (P0, AC5, R-005)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "github_reference", json.dumps(["owner", "repo"]))

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_github_reference"

    def test_malformed_provider_metadata_json_returns_diagnostic_no_exception(self, conn, tmp_path):
        """2.1B-INT-006 (P0, AC5, R-005)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "provider_metadata", "{not valid json")

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_provider_metadata"
        assert "invalid_provider_metadata" in {d["category"] for d in result["diagnostics"]}

    def test_provider_metadata_non_dict_json_returns_diagnostic_no_exception(self, conn, tmp_path):
        """2.1B-INT-007 (P0, AC5, R-005): provider metadata JSON that parses
        to a non-dict must not crash `validate_binding()`."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "provider_metadata", json.dumps([1, 2, 3]))

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_provider_metadata"

    def test_one_sided_provider_identity_raw_row_returns_diagnostic_no_exception(
        self, conn, tmp_path
    ):
        """2.1B-INT-007/030 (P0/P1, AC5, R-005): a persisted row with
        `provider_name` set but `provider_binding_name` NULL (only
        reachable via an out-of-band write, since `create_binding()`
        rejects this shape) must degrade to a diagnostic, not an
        exception."""
        created = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path, provider_name=None, provider_binding_name=None, provider_metadata=None
            ),
        )
        set_raw_column(conn, created["id"], "provider_name", "archon")

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_provider_metadata"
        assert "invalid_provider_metadata" in {d["category"] for d in result["diagnostics"]}

    def test_provider_metadata_without_identity_raw_row_returns_diagnostic(self, conn, tmp_path):
        """2.1B-INT-007/030 (P0/P1, AC5, R-005): metadata present without a
        complete Controller Identity (only reachable via an out-of-band
        write)."""
        created = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path, provider_name=None, provider_binding_name=None, provider_metadata=None
            ),
        )
        set_raw_column(
            conn, created["id"], "provider_metadata", json.dumps({"bindingId": "wpb_x"})
        )

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["validation_state"] == "invalid_provider_metadata"

    def test_unknown_binding_id_raises_value_error(self, conn):
        """2.1B-INT-017 (P1, R-015): a binding id that resolves to no row
        is a caller/programmer error, not a validation outcome."""
        before = row_count(conn)
        with pytest.raises(ValueError):
            pb.validate_binding(conn, "pb_doesnotexist")
        assert row_count(conn) == before

    def test_validation_state_precedence_cwd_wins_over_everything(self, conn, tmp_path):
        """2.1B-INT-013 (P0, AC1/AC4/AC5, R-009): when cwd AND bmad AND
        github AND provider are all simultaneously invalid,
        `validation_state` must be `invalid_cwd` (highest precedence)."""
        never_existed = str(tmp_path / "never-existed")
        missing_bmad = str(tmp_path / "missing-bmad")
        created = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path, bound_project_cwd=never_existed, bmad_skill_dir=missing_bmad
            ),
        )
        set_raw_column(conn, created["id"], "github_reference", "{not valid json")
        set_raw_column(conn, created["id"], "provider_metadata", "{not valid json")

        result = pb.validate_binding(conn, created["id"])
        assert result["validation_state"] == "invalid_cwd"
        assert result["safe"] is False

    def test_validation_state_precedence_bmad_before_github_and_provider(self, conn, tmp_path):
        """2.1B-INT-013 (P0, AC1/AC4/AC5, R-009): with a VALID cwd but
        invalid bmad + github + provider simultaneously, `validation_state`
        must be `invalid_bmad_reference` (second-highest precedence)."""
        missing_bmad = str(tmp_path / "missing-bmad")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bmad_skill_dir=missing_bmad)
        )
        set_raw_column(conn, created["id"], "github_reference", "{not valid json")
        set_raw_column(conn, created["id"], "provider_metadata", "{not valid json")

        result = pb.validate_binding(conn, created["id"])
        assert result["validation_state"] == "invalid_bmad_reference"

    def test_validation_state_precedence_github_before_provider(self, conn, tmp_path):
        """2.1B-INT-013 (P0, AC1/AC5, R-009): with valid cwd/bmad but
        invalid github + provider simultaneously, `validation_state` must
        be `invalid_github_reference` (ahead of
        `invalid_provider_metadata`)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "github_reference", "{not valid json")
        set_raw_column(conn, created["id"], "provider_metadata", "{not valid json")

        result = pb.validate_binding(conn, created["id"])
        assert result["validation_state"] == "invalid_github_reference"

    def test_safe_iff_all_checks_valid_and_conflicts_empty(self, conn, tmp_path):
        """2.1B-INT-014 (P0, AC1/AC4/AC5/AC6, R-009): `safe` is exactly the
        conjunction of every check's validity (or `None` for the optional
        BMAD check) and an empty conflicts list — never computed
        independently."""
        valid_created = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path,
                repo_name="valid-one",
                bmad_name="bmad-valid",
                github_reference={"owner": "Org", "repo": "valid-one"},
                provider_binding_name="engine-valid",
            ),
        )
        valid_result = pb.validate_binding(conn, valid_created["id"])
        assert valid_result["safe"] is True
        assert valid_result["validation_state"] == "valid"

        never_existed = str(tmp_path / "never-existed-2")
        invalid_created = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path,
                repo_name="invalid-one",
                bmad_name="bmad-invalid",
                bound_project_cwd=never_existed,
                github_reference={"owner": "Org", "repo": "invalid-one"},
                provider_binding_name="engine-invalid",
            ),
        )
        invalid_result = pb.validate_binding(conn, invalid_created["id"])
        assert invalid_result["safe"] is False

    def test_never_reports_self_as_conflict(self, conn, tmp_path):
        """2.1B-INT-015 (P1, AC2/AC6, R-007): a binding created through
        `create_binding()` must never be reported as conflicting with
        itself when re-validated. Doubles as the Task 4 critical
        invariant test — no two persisted rows in one profile can collide
        on any dimension (hard partial unique indexes), so this is the
        only reachable outcome for the existing-binding conflict scan
        today (see W-11)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        result = pb.validate_binding(conn, created["id"])
        assert result["conflicts"] == []

    def test_exclude_binding_id_only_excludes_the_specified_row(self, conn, tmp_path):
        """2.1B-INT-016 (P1, AC2, R-007): `_check_uniqueness_dimensions(...,
        exclude_binding_id=...)` must exclude that row's own SQL match, but
        still find a DIFFERENT sibling colliding on the same dimension —
        proving exclusion is per-row, not "skip all matches"."""
        a = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path,
                repo_name="a-repo",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
        )
        b = pb.create_binding(
            conn,
            **real_binding_kwargs(
                tmp_path,
                repo_name="b-repo",
                github_reference=None,
                bmad_skill_dir=None,
                provider_name=None,
                provider_binding_name=None,
                provider_metadata=None,
            ),
        )
        a_cwd = pb._normalize_path(str(tmp_path / "a-repo"))

        self_excluded = pb._check_uniqueness_dimensions(
            conn, "default", a_cwd, None, None, None, None, exclude_binding_id=a["id"]
        )
        assert "bound_project_cwd" not in self_excluded

        sibling_found = pb._check_uniqueness_dimensions(
            conn, "default", a_cwd, None, None, None, None, exclude_binding_id=b["id"]
        )
        assert sibling_found.get("bound_project_cwd") == a["id"]

    def test_one_malformed_field_does_not_prevent_other_checks(self, conn, tmp_path):
        """2.1B-INT-020 (P0, AC5, R-005): when only `github_reference` is
        malformed, `validate_binding()` must still assemble the cwd, bmad,
        and provider_metadata checks plus the conflict scan, not
        short-circuit."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "github_reference", "{not valid json")

        result = pb.validate_binding(conn, created["id"])
        assert result["cwd_check"] == {"valid": True, "reason": None}
        assert result["bmad_reference_check"] == {"valid": True, "reason": None}
        assert result["github_reference_check"]["valid"] is False
        assert result["provider_metadata_check"] == {"valid": True, "reason": None}
        assert result["conflicts"] == []

    def test_stale_cwd_deleted_after_create_becomes_unsafe(self, conn, tmp_path):
        """2.1B-INT-027 (P1, AC1, R-013): revalidation must use current
        filesystem state — a directory deleted after the binding was
        created must be caught, not just what was true at create time."""
        repo = _make_git_repo(tmp_path, "will-be-deleted")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bound_project_cwd=str(repo))
        )
        assert pb.validate_binding(conn, created["id"])["safe"] is True

        shutil.rmtree(repo)

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["cwd_check"]["reason"] == "cwd_does_not_exist"

    def test_stale_git_removed_after_create_becomes_unsafe(self, conn, tmp_path):
        """2.1B-INT-028 (P1, AC3, R-013)."""
        repo = _make_git_repo(tmp_path, "git-will-be-removed")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bound_project_cwd=str(repo))
        )
        assert pb.validate_binding(conn, created["id"])["safe"] is True

        shutil.rmtree(repo / ".git")

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert result["cwd_check"]["reason"] == "cwd_is_not_a_git_repository"

    def test_stale_bmad_dir_deleted_after_create_becomes_unsafe(self, conn, tmp_path):
        """2.1B-INT-029 (P1, AC4, R-013)."""
        bmad_dir = _make_plain_dir(tmp_path, "bmad-will-be-deleted")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bmad_skill_dir=str(bmad_dir))
        )
        assert pb.validate_binding(conn, created["id"])["safe"] is True

        shutil.rmtree(bmad_dir)

        result = pb.validate_binding(conn, created["id"])
        assert result["safe"] is False
        assert "invalid_bmad_reference" in {d["category"] for d in result["diagnostics"]}

    def test_diagnostic_messages_are_nonempty_actionable_and_tagged(self, conn, tmp_path):
        """2.1B-INT-031 (P1, AC1/AC2/AC4/AC5, R-008): every diagnostic
        entry carries a nonempty, human-actionable message and the
        affected local category — never a placeholder or blank string."""
        never_existed = str(tmp_path / "never-existed-3")
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bound_project_cwd=never_existed)
        )
        result = pb.validate_binding(conn, created["id"])
        assert result["diagnostics"], "expected at least one diagnostic"
        for diag in result["diagnostics"]:
            assert isinstance(diag["message"], str) and diag["message"].strip()
            assert isinstance(diag["category"], str) and diag["category"].strip()

    def test_validate_binding_conflict_diagnostic_uses_update_project_binding(
        self, conn, tmp_path, monkeypatch
    ):
        """2.1B-CONTRACT-001 (partial, P0, AC2, R-007/R-008, W-11):
        `validate_binding()`'s existing-binding conflict scan can never
        observe a real non-empty result through supported writes (hard
        partial unique indexes make two persisted colliding rows
        impossible — see W-11 and Task 4's own critical invariant note).
        To still exercise the conflict-diagnostic assembly branch
        (category mapping + `recovery_option: "update_project_binding"`),
        force the shared dimension-check seam
        (`_check_uniqueness_dimensions`, reused by both
        `preview_binding_conflicts` and `validate_binding`'s re-scan per
        Task 5) to report a synthetic collision for this call only. This
        never persists a second colliding row — it only proves the
        diagnostic-assembly branch is wired correctly."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))

        def _fake_check(*args, **kwargs):
            return {"bound_project_cwd": "pb_other_binding"}

        monkeypatch.setattr(pb, "_check_uniqueness_dimensions", _fake_check)

        result = pb.validate_binding(conn, created["id"])

        assert result["conflicts"] == [
            {"category": "cwd_conflict", "conflicting_binding_id": "pb_other_binding"}
        ]
        conflict_diag = next(
            d for d in result["diagnostics"] if d["category"] == "cwd_conflict"
        )
        assert conflict_diag["next_action_owner"] == "configuration"
        assert conflict_diag["recovery_option"] == "update_project_binding"
        assert result["validation_state"] == "conflicting"
        assert result["safe"] is False


class TestDiagnosticContractVocabulary:
    """Contract tests for `validate_binding()`'s diagnostic vocabulary
    (Story 2.1b, Task 5 bullet 5): exact `next_action_owner`/
    `recovery_option`/category strings, reusing the operational-diagnostic
    schema's existing enum values for forward compatibility with Story
    5.3a."""

    def test_invalid_cwd_diagnostic_uses_repair_project_binding(self, conn, tmp_path):
        """2.1B-CONTRACT-001 (P0, AC1, R-008)."""
        created = pb.create_binding(
            conn, **real_binding_kwargs(tmp_path, bound_project_cwd=str(tmp_path / "gone"))
        )
        result = pb.validate_binding(conn, created["id"])
        matching = [d for d in result["diagnostics"] if d["category"] == "invalid_cwd"]
        assert matching
        for diag in matching:
            assert diag["next_action_owner"] == "configuration"
            assert diag["recovery_option"] == "repair_project_binding"

    def test_invalid_bmad_reference_diagnostic_uses_repair_project_binding(self, conn, tmp_path):
        """2.1B-CONTRACT-001 (P0, AC4, R-008)."""
        created = pb.create_binding(
            conn,
            **real_binding_kwargs(tmp_path, bmad_skill_dir=str(tmp_path / "gone-bmad")),
        )
        result = pb.validate_binding(conn, created["id"])
        matching = [
            d for d in result["diagnostics"] if d["category"] == "invalid_bmad_reference"
        ]
        assert matching
        for diag in matching:
            assert diag["next_action_owner"] == "configuration"
            assert diag["recovery_option"] == "repair_project_binding"

    def test_invalid_github_reference_diagnostic_uses_repair_project_binding(self, conn, tmp_path):
        """2.1B-CONTRACT-001 (P0, AC5, R-008)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "github_reference", "{not valid json")
        result = pb.validate_binding(conn, created["id"])
        matching = [
            d for d in result["diagnostics"] if d["category"] == "invalid_github_reference"
        ]
        assert matching
        for diag in matching:
            assert diag["next_action_owner"] == "configuration"
            assert diag["recovery_option"] == "repair_project_binding"

    def test_invalid_provider_metadata_diagnostic_uses_repair_project_binding(
        self, conn, tmp_path
    ):
        """2.1B-CONTRACT-001 (P0, AC5, R-008)."""
        created = pb.create_binding(conn, **real_binding_kwargs(tmp_path))
        set_raw_column(conn, created["id"], "provider_metadata", "{not valid json")
        result = pb.validate_binding(conn, created["id"])
        matching = [
            d for d in result["diagnostics"] if d["category"] == "invalid_provider_metadata"
        ]
        assert matching
        for diag in matching:
            assert diag["next_action_owner"] == "configuration"
            assert diag["recovery_option"] == "repair_project_binding"

    def test_conflict_categories_map_exact_dimension_strings(self, conn, tmp_path):
        """2.1B-CONTRACT-001 (P0, AC2/AC7, R-006/R-008):
        `preview_binding_conflicts()` maps each
        `_check_uniqueness_dimensions()` key to the exact local category
        string this story defines."""
        pb.create_binding(conn, **real_binding_kwargs(tmp_path, repo_name="target"))
        result = pb.preview_binding_conflicts(
            conn,
            profile="default",
            bound_project_cwd=str(tmp_path / "target"),
            github_reference={"owner": "NousResearch", "repo": "hermes-agent"},
            bmad_skill_dir=str(tmp_path / "_bmad"),
            provider_name="archon",
            provider_binding_name="workflow-engine-primary",
        )
        assert {c["category"] for c in result} == {
            "cwd_conflict",
            "github_reference_conflict",
            "bmad_mount_conflict",
            "provider_identity_conflict",
        }


class TestScopeRegressionGuards:
    """Regression/static guards for Story 2.1b's own Dev Notes scope
    boundary. Unlike the rest of this section, these assert the CURRENT
    absence of scope-creep surface — they should PASS today and continue
    passing after implementation; they exist to catch scope creep, not to
    encode not-yet-built behavior."""

    def test_no_new_lifecycle_or_audit_columns_added(self, conn):
        """2.1B-REG-001 (P1, R-010, W-02): `validate_binding()` requires no
        new database columns. Schema PRAGMA must show exactly the columns
        2.1a defined — no `enabled`, durable `validation_state`, or audit
        columns."""
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(project_bindings)")}
        assert columns == pb._EXPECTED_COLUMNS
        assert "enabled" not in columns
        assert "validation_state" not in columns

    def test_no_activation_or_lifecycle_functions_added(self):
        """2.1B-REG-003 (P1, R-010, W-01/W-02/W-05): this story must not add
        an `activate_binding()`/`enable_binding()`/`disable_binding()`/
        `update_binding()` command surface — those belong to Story
        2.1c/2.3."""
        forbidden_names = (
            "activate_binding",
            "enable_binding",
            "disable_binding",
            "update_binding",
            "repair_binding",
        )
        for name in forbidden_names:
            assert not hasattr(pb, name), f"unexpected scope-creep function: {name}"

    def test_no_cli_or_toolset_wiring_references_new_validation_functions(self):
        """2.1B-REG-003 (P1, R-010, W-01): no CLI command or tool registry
        wiring should call `validate_binding()`/`preview_binding_conflicts()`
        yet — that wiring belongs to later stories (2.3, 2.4) per this
        story's Dev Notes "Project Structure Notes"."""
        candidate_files = [REPO_ROOT / "cli.py", REPO_ROOT / "toolsets.py"]
        for path in candidate_files:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            assert "validate_binding(" not in text, (
                f"{path} should not wire validate_binding() yet"
            )
            assert "preview_binding_conflicts(" not in text, (
                f"{path} should not wire preview_binding_conflicts() yet"
            )

    def test_migration_seam_unchanged_no_new_column_ddl(self, db_path):
        """2.1B-REG-001 (P1, R-010, W-02): the `_migrate_add_optional_columns()`
        seam stays reserved for Story 2.1c — connecting twice must not
        introduce any column beyond 2.1a's schema."""
        conn1 = pb.connect(db_path=db_path)
        try:
            first = {row["name"] for row in conn1.execute("PRAGMA table_info(project_bindings)")}
        finally:
            conn1.close()
        conn2 = pb.connect(db_path=db_path)
        try:
            second = {row["name"] for row in conn2.execute("PRAGMA table_info(project_bindings)")}
        finally:
            conn2.close()
        assert first == second == pb._EXPECTED_COLUMNS


# =============================================================================
# Contract validation (executable now — targets the already-shipped fixture
# package, not hermes_project_work; not gated by the module skip above)
# =============================================================================


def test_workflow_commander_contract_validator_passes():
    """2.1A-VAL-001 (Contract validation, R-013): the shipped Workflow
    Commander contract validator and its committed fixtures (including
    status-valid.json, the real v1 provider-binding fixture INT-016 loads)
    must pass. This targets an already-shipped artifact independent of
    hermes_project_work, so unlike the rest of this file it runs now and is
    expected to already be green — a regression guard, not a red-phase test."""
    result = subprocess.run(
        [sys.executable, str(VALIDATE_CONTRACTS_SCRIPT)],
        cwd=str(CONTRACTS_DIR),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
