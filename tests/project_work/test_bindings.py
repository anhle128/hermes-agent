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
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import re
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
except ImportError:  # pragma: no cover - expected until Task 1 lands
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
        ],
        ids=[
            "missing-binding-name",
            "missing-provider-name",
            "blank-provider-name",
            "blank-binding-name",
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
        tests/stress/test_atypical_scenarios.py::_idempotency_race_worker."""
        db_file = tmp_path / "project_bindings.db"
        barrier = tmp_path / "barrier"
        results = [tmp_path / f"race_result_{i}.json" for i in range(2)]
        ctx = mp.get_context("spawn")
        procs = [
            ctx.Process(
                target=_race_worker,
                args=(os.environ["HERMES_HOME"], str(db_file), str(results[i]), str(barrier)),
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
        reopen — concurrency must not corrupt unrelated rows."""
        db_file = tmp_path / "project_bindings.db"
        barrier = tmp_path / "barrier"
        results = [tmp_path / f"distinct_result_{i}.json" for i in range(2)]
        cwds = ["/tmp/race-distinct-a", "/tmp/race-distinct-b"]
        ctx = mp.get_context("spawn")
        procs = [
            ctx.Process(
                target=_distinct_race_worker,
                args=(
                    os.environ["HERMES_HOME"],
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
        assert len(indexes) >= 4, "expected at least the four partial unique indexes"
        for index in indexes:
            assert index["unique"] == 1


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
        closed — never silently overwrite the first row. The exact private
        id-generator seam name is illustrative; adjust to the actual helper."""
        id_gen_name = "_new_binding_id"
        if not hasattr(pb, id_gen_name):
            pytest.skip(f"pb.{id_gen_name} not present; adjust to actual id generator name")

        monkeypatch.setattr(pb, id_gen_name, lambda: "pb_00000000")

        first = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/first"))
        second = pb.create_binding(conn, **valid_kwargs(bound_project_cwd="/tmp/second"))

        assert first["id"] == "pb_00000000"
        # A colliding id must not silently overwrite: either the second call
        # fails closed (conflict/error) or it retries with a fresh id — but it
        # must never share the first row's id while both rows persist.
        if second.get("conflict"):
            assert row_count(conn) == 1
        else:
            assert second["id"] != first["id"]
            assert row_count(conn) == 2


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
