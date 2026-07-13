"""Per-profile Project Binding store.

A **Project Binding** is an explicit, persisted link between a Hermes profile
and a concrete project identity: a working directory, an optional GitHub
reference, an optional BMAD skill directory reference, and optional workflow
provider binding metadata.  Unlike the desktop's ``projects.db`` (a
multi-folder workspace grouping), a Project Binding anchors the workflow
pipeline's forward ownership: every later action (BMAD mounting,
materialization, phase tasks) resolves through a binding.

Scope: **per-profile**, stored at ``$HERMES_HOME/project_bindings.db``
(resolved via ``get_hermes_home()``).  The ``profile`` column on each row
makes it self-describing even if a misconfigured subprocess writes into the
wrong profile's DB file (see ``hermes_constants.py`` fallback bug #18594).

Schema evolution is additive: ``_migrate_add_optional_columns()`` is called
on every ``connect()`` so the next story (2.1b/2.1c) can add columns without
a rewrite.
"""

from __future__ import annotations

import contextlib
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from hermes_cli.sqlite_util import add_column_if_missing as _add_column_if_missing, write_txn
from hermes_constants import get_hermes_home


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def project_bindings_db_path() -> Path:
    """The per-profile project bindings DB path.

    Profile-aware: ``get_hermes_home()`` already points at the active
    profile's home.  Tests pass an explicit ``db_path`` to :func:`connect`.
    """
    return get_hermes_home() / "project_bindings.db"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS project_bindings (
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
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_INITIALIZED_PATHS: set[str] = set()


def _new_binding_id() -> str:
    return "pb_" + secrets.token_hex(4)


def _now() -> int:
    return int(time.time())


def _normalize_path(path: str) -> str:
    """Absolute, user-expanded, separator-normalized path.

    Root (``"/"``) stays root — the ``or path`` guard prevents stripping it
    to an empty string.  Null bytes are rejected — they cause silent
    truncation in SQLite and C-level path operations.  Input must be a
    string — non-string types are rejected to prevent silent coercion.
    """
    if not isinstance(path, str):
        raise TypeError(f"path must be a string, got {type(path).__name__}")
    if "\x00" in path:
        raise ValueError("path must not contain null bytes")
    p = os.path.abspath(os.path.expanduser(path.strip()))
    return p.rstrip("/\\") or p


def _github_reference_key(ref: dict) -> str:
    """Canonical, deterministic key for GitHub reference uniqueness.

    Lowercased ``owner/repo`` — never ``json.dumps`` equality, which is
    key-order-dependent.
    """
    return f"{ref['owner'].strip().lower()}/{ref['repo'].strip().lower()}"


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


def _is_lock_error(exc: sqlite3.OperationalError) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Run schema init idempotently.

    ``executescript`` issues an implicit COMMIT and runs DDL, which requires
    a write lock.  When another connection holds an IMMEDIATE lock (e.g. a
    concurrent writer), this raises ``OperationalError``.  We do NOT swallow
    errors here — if schema init fails, the connection is unusable and the
    caller must retry.  Lock errors are retried by ``connect()``.
    """
    from hermes_state import apply_wal_with_fallback

    apply_wal_with_fallback(conn, db_label="project_bindings.db")
    conn.executescript(SCHEMA_SQL)
    _migrate_add_optional_columns(conn)


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open and initialize the per-profile project bindings DB.

    Schema init is idempotent (``CREATE TABLE IF NOT EXISTS``, ``CREATE
    UNIQUE INDEX IF NOT EXISTS``) and handles file recreation after external
    deletion.  If the DB is locked by another writer, initialization is
    retried with bounded backoff.  WAL with DELETE fallback via the shared
    helper.  ``check_same_thread=False`` allows cross-thread use (needed for
    concurrent-init tests).
    """
    path = db_path if db_path is not None else project_bindings_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved = str(path.resolve())
    conn = sqlite3.connect(str(path), check_same_thread=False)
    try:
        conn.row_factory = sqlite3.Row
        _init_connection_with_retry(conn)
        _INITIALIZED_PATHS.add(resolved)
    except Exception:
        conn.close()
        raise
    return conn


_SCHEMA_INIT_RETRIES = 5
_SCHEMA_INIT_BACKOFF_MS = 10


def _init_connection_with_retry(conn: sqlite3.Connection) -> None:
    """Retry WAL + schema init on lock errors; raise on all other failures."""
    from hermes_state import apply_wal_with_fallback

    for attempt in range(_SCHEMA_INIT_RETRIES):
        try:
            apply_wal_with_fallback(conn, db_label="project_bindings.db")
            conn.execute("PRAGMA foreign_keys=ON")
            _ensure_schema(conn)
            return
        except sqlite3.OperationalError as exc:
            if _is_lock_error(exc) and attempt < _SCHEMA_INIT_RETRIES - 1:
                time.sleep(_SCHEMA_INIT_BACKOFF_MS * (attempt + 1) / 1000.0)
                continue
            raise


@contextlib.contextmanager
def connect_closing(db_path: Optional[Path] = None):
    """Open a connection and guarantee it is closed on exit."""
    conn = connect(db_path=db_path)
    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


def _migrate_add_optional_columns(conn: sqlite3.Connection) -> None:
    """Forward-compat seam for future stories (2.1b/2.1c).

    Called on every ``connect()`` so the next story can add
    ``enabled``/``validation_state``/audit columns additively via
    ``add_column_if_missing`` without rewriting ``connect()``.
    """


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass
class ProjectBinding:
    id: str
    profile: str
    display_name: str
    bound_project_cwd: str
    created_at: int
    github_reference: Optional[dict] = None
    bmad_skill_dir: Optional[str] = None
    provider_name: Optional[str] = None
    provider_binding_name: Optional[str] = None
    provider_metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "profile": self.profile,
            "display_name": self.display_name,
            "bound_project_cwd": self.bound_project_cwd,
            "github_reference": self.github_reference,
            "bmad_skill_dir": self.bmad_skill_dir,
            "provider_name": self.provider_name,
            "provider_binding_name": self.provider_binding_name,
            "provider_metadata": self.provider_metadata,
            "created_at": self.created_at,
        }


def _binding_from_row(row: sqlite3.Row) -> ProjectBinding:
    gh_raw = row["github_reference"]
    gh = json.loads(gh_raw) if gh_raw is not None else None
    pm_raw = row["provider_metadata"]
    pm = json.loads(pm_raw) if pm_raw is not None else None
    return ProjectBinding(
        id=row["id"],
        profile=row["profile"],
        display_name=row["display_name"],
        bound_project_cwd=row["bound_project_cwd"],
        github_reference=gh,
        bmad_skill_dir=row["bmad_skill_dir"],
        provider_name=row["provider_name"],
        provider_binding_name=row["provider_binding_name"],
        provider_metadata=pm,
        created_at=row["created_at"],
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _resolve_profile(profile: Optional[str]) -> str:
    """Resolve ``None`` → active profile name, falling back to ``"default"``.

    The resolved name is stripped of leading/trailing whitespace for
    canonical form.  Non-string types are rejected.
    """
    if profile is None:
        try:
            from hermes_cli.profiles import get_active_profile_name
            return get_active_profile_name().strip()
        except Exception:
            return "default"
    if not isinstance(profile, str):
        raise TypeError(f"profile must be a string, got {type(profile).__name__}")
    return profile.strip()


def _require_nonblank_str(value: object, field_name: str) -> str:
    if value is None:
        raise TypeError(f"{field_name} must be a non-empty string, got None")
    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")
    return value


def _validate_github_reference(
    ref: object,
) -> Optional[dict]:
    if ref is None:
        return None
    if not isinstance(ref, dict):
        raise ValueError(
            "github_reference must be a dict with 'owner' and 'repo' keys"
        )
    owner = ref.get("owner")
    repo = ref.get("repo")
    if not isinstance(owner, str) or not owner.strip():
        raise ValueError("github_reference['owner'] must be a non-empty string")
    if not isinstance(repo, str) or not repo.strip():
        raise ValueError("github_reference['repo'] must be a non-empty string")
    if "/" in owner:
        raise ValueError("github_reference['owner'] must not contain '/'")
    if "/" in repo:
        raise ValueError("github_reference['repo'] must not contain '/'")
    return ref


def _validate_provider_identity(
    provider_name: Optional[str],
    provider_binding_name: Optional[str],
    provider_metadata: Optional[dict] = None,
) -> None:
    has_name = (
        isinstance(provider_name, str) and bool(provider_name.strip())
    )
    has_binding = (
        isinstance(provider_binding_name, str) and bool(provider_binding_name.strip())
    )
    if has_name != has_binding:
        raise ValueError(
            "provider_name and provider_binding_name must both be "
            "present and non-blank, or both absent"
        )
    if provider_metadata is not None:
        if not isinstance(provider_metadata, dict):
            raise TypeError(
                f"provider_metadata must be a dict, got {type(provider_metadata).__name__}"
            )
        if not has_name or not has_binding:
            raise ValueError(
                "provider_metadata requires both provider_name and "
                "provider_binding_name (Controller Identity)"
            )


def _serialize_json(value: dict, field_name: str) -> str:
    """Serialize to JSON, rejecting non-standard constants and unfaithful round-trips."""
    try:
        serialized = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise type(exc)(
            f"{field_name} is not valid JSON-serializable data: {exc}"
        ) from None
    round_tripped = json.loads(serialized)
    if round_tripped != value:
        raise ValueError(
            f"{field_name} did not survive a JSON round-trip faithfully "
            f"(input type changed during serialization)"
        )
    return serialized


# ---------------------------------------------------------------------------
# Uniqueness pre-check
# ---------------------------------------------------------------------------


def _check_uniqueness_dimensions(
    conn: sqlite3.Connection,
    profile: str,
    normalized_cwd: str,
    github_key: Optional[str],
    normalized_bmad_dir: Optional[str],
    provider_name: Optional[str],
    provider_binding_name: Optional[str],
) -> dict[str, str]:
    """Return ``{dimension: existing_id}`` for every colliding dimension."""
    violations: dict[str, str] = {}

    row = conn.execute(
        "SELECT id FROM project_bindings"
        " WHERE profile = ? AND bound_project_cwd = ?",
        (profile, normalized_cwd),
    ).fetchone()
    if row:
        violations["bound_project_cwd"] = row["id"]

    if github_key is not None:
        row = conn.execute(
            "SELECT id FROM project_bindings"
            " WHERE profile = ? AND github_reference_key = ?",
            (profile, github_key),
        ).fetchone()
        if row:
            violations["github_reference_key"] = row["id"]

    if normalized_bmad_dir is not None:
        row = conn.execute(
            "SELECT id FROM project_bindings"
            " WHERE profile = ? AND bmad_skill_dir = ?",
            (profile, normalized_bmad_dir),
        ).fetchone()
        if row:
            violations["bmad_skill_dir"] = row["id"]

    if provider_name is not None and provider_binding_name is not None:
        row = conn.execute(
            "SELECT id FROM project_bindings"
            " WHERE profile = ? AND provider_name = ?"
            " AND provider_binding_name = ?",
            (profile, provider_name, provider_binding_name),
        ).fetchone()
        if row:
            violations["provider_identity"] = row["id"]

    return violations


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

_MAX_ID_RETRIES = 10


def create_binding(
    conn: sqlite3.Connection,
    *,
    profile: Optional[str] = None,
    display_name: str,
    bound_project_cwd: str,
    github_reference: Optional[dict] = None,
    bmad_skill_dir: Optional[str] = None,
    provider_name: Optional[str] = None,
    provider_binding_name: Optional[str] = None,
    provider_metadata: Optional[dict] = None,
) -> dict:
    """Create a Project Binding.

    Returns ``{"conflict": False, "id": "pb_..."}`` on success or
    ``{"conflict": True, "violations": {dimension: existing_id, ...}}``
    on any uniqueness collision.  Raises ``ValueError``/``TypeError`` for
    invalid inputs *before* any SQL mutation.
    """
    resolved_profile = _resolve_profile(profile)
    _require_nonblank_str(resolved_profile, "profile")
    _require_nonblank_str(display_name, "display_name")
    _require_nonblank_str(bound_project_cwd, "bound_project_cwd")

    gh_ref = _validate_github_reference(github_reference)
    _validate_provider_identity(provider_name, provider_binding_name, provider_metadata)

    normalized_cwd = _normalize_path(bound_project_cwd)
    normalized_bmad = (
        _normalize_path(bmad_skill_dir) if bmad_skill_dir is not None else None
    )
    gh_key = _github_reference_key(gh_ref) if gh_ref else None

    pn = provider_name.strip() if isinstance(provider_name, str) else None
    pbn = (
        provider_binding_name.strip()
        if isinstance(provider_binding_name, str)
        else None
    )

    gh_json = (
        _serialize_json(gh_ref, "github_reference") if gh_ref else None
    )
    pm_json = (
        _serialize_json(provider_metadata, "provider_metadata")
        if provider_metadata is not None
        else None
    )

    _ensure_schema(conn)

    now = _now()

    for _ in range(_MAX_ID_RETRIES):
        binding_id = _new_binding_id()

        try:
            with write_txn(conn):
                violations = _check_uniqueness_dimensions(
                    conn,
                    resolved_profile,
                    normalized_cwd,
                    gh_key,
                    normalized_bmad,
                    pn,
                    pbn,
                )
                if violations:
                    return {"conflict": True, "violations": violations}

                conn.execute(
                    "INSERT INTO project_bindings"
                    " (id, profile, display_name, bound_project_cwd,"
                    " github_reference, github_reference_key,"
                    " bmad_skill_dir, provider_name,"
                    " provider_binding_name, provider_metadata,"
                    " created_at)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        binding_id,
                        resolved_profile,
                        display_name,
                        normalized_cwd,
                        gh_json,
                        gh_key,
                        normalized_bmad,
                        pn,
                        pbn,
                        pm_json,
                        now,
                    ),
                )
            return {"conflict": False, "id": binding_id}
        except sqlite3.IntegrityError:
            race = _check_uniqueness_dimensions(
                conn,
                resolved_profile,
                normalized_cwd,
                gh_key,
                normalized_bmad,
                pn,
                pbn,
            )
            if race:
                return {"conflict": True, "violations": race}
            continue

    raise RuntimeError(
        f"failed to generate a unique binding id after {_MAX_ID_RETRIES} retries"
    )


def get_binding(
    conn: sqlite3.Connection, binding_id: str
) -> Optional[ProjectBinding]:
    row = conn.execute(
        "SELECT * FROM project_bindings WHERE id = ?", (binding_id,)
    ).fetchone()
    if row is None:
        return None
    return _binding_from_row(row)


def list_bindings_for_profile(
    conn: sqlite3.Connection, profile: str
) -> List[ProjectBinding]:
    rows = conn.execute(
        "SELECT * FROM project_bindings WHERE profile = ?"
        " ORDER BY created_at ASC",
        (profile,),
    ).fetchall()
    return [_binding_from_row(r) for r in rows]
