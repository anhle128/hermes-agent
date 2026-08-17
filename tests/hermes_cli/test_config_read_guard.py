"""Lint guard: no new raw yaml.safe_load(config.yaml) reads outside owner modules.

The drift class this kills: scattered ``yaml.safe_load`` reads of the user's
``config.yaml`` silently miss the managed-scope overlay, ``${ENV_VAR}``
expansion, profile-aware pathing, and root-model normalization. Each new
config feature has historically required an N-site sweep (incident chain:
9cbcc0c9c8 → 732293cf87 → b0e47a98f9 → 1928aa0443).

Canonical owners:

  * ``hermes_cli/config.py`` — ``load_config()`` / ``load_config_readonly()``
    (merged + managed + env-expanded), ``read_raw_config()`` and
    ``read_user_config_raw()`` (the ONLY legal raw primitives: write-back
    round-trips + raw-file diagnostics).
  * ``gateway/config.py`` — the gateway's ``load_gateway_config`` owner.
  * ``gateway/run.py`` — ``_load_gateway_config()``'s monkeypatched-home
    fallback path (delegates to ``read_raw_config`` when paths agree).

Everything else must import one of those. If this test fails on your new
code, use ``load_config()``/``load_config_readonly()`` for behavioral reads,
or ``read_user_config_raw()`` for write-back round-trips — do not add your
file to the allowlist without a reason of the same class.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Files where a yaml.safe_load near a config.yaml reference is legal.
# Keep this list SHORT and justified:
ALLOWLIST = {
    # Canonical loader owners.
    "hermes_cli/config.py",
    "gateway/config.py",
    # _load_gateway_config()'s fallback path for tests that monkeypatch
    # gateway.run._hermes_home (delegates to read_raw_config otherwise).
    "gateway/run.py",
    # Reads the MANAGED-scope config.yaml (/etc/hermes/...), not the user's —
    # it IS the overlay source; the canonical loaders call into it.
    "hermes_cli/managed_scope.py",
    # Parse-health probe: intentionally answers "does the raw file parse?".
    "gateway/readiness.py",
}

# Directories that never count (tests may build fixture configs freely).
EXCLUDED_DIR_PARTS = {
    "tests", ".venv", ".git", ".worktrees", "node_modules", "website",
    "docs", "scripts", "examples", "apps",
}

# A safe_load within this many lines of a config.yaml reference is treated
# as a raw user-config read.
PROXIMITY = 6

SAFE_LOAD_RE = re.compile(r"\bsafe_load\s*\(")
CONFIG_YAML_RE = re.compile(r"""["']config\.yaml["']""")


def _iter_source_files(root: Path = REPO_ROOT):
    def fail_walk_error(error: OSError) -> None:
        if isinstance(error, FileNotFoundError) and error.filename and Path(error.filename) != root:
            return
        raise error

    for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=fail_walk_error):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDED_DIR_PARTS]
        current = Path(dirpath)
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            path = current / filename
            yield path.relative_to(root), path


def test_iter_source_files_prunes_excluded_dirs_before_traversal(tmp_path):
    included = tmp_path / "hermes_cli" / "config.py"
    included.parent.mkdir()
    included.write_text("", encoding="utf-8")
    excluded = tmp_path / "tests" / "__pycache__" / "gone.py"
    excluded.parent.mkdir(parents=True)
    excluded.write_text("", encoding="utf-8")

    assert list(_iter_source_files(tmp_path)) == [(Path("hermes_cli/config.py"), included)]


def test_iter_source_files_ignores_vanished_child_dirs(tmp_path, monkeypatch):
    included = tmp_path / "hermes_cli" / "config.py"
    included.parent.mkdir()
    included.write_text("", encoding="utf-8")
    error = FileNotFoundError("lost")
    error.filename = str(tmp_path / ".claude" / "skills" / "gone" / "__pycache__")

    def flaky_walk(root, topdown=True, onerror=None):
        assert root == tmp_path
        assert topdown is True
        assert onerror is not None
        onerror(error)
        yield str(included.parent), [], [included.name]

    monkeypatch.setattr(os, "walk", flaky_walk)

    assert list(_iter_source_files(tmp_path)) == [(Path("hermes_cli/config.py"), included)]


def test_iter_source_files_propagates_included_traversal_errors(tmp_path, monkeypatch):
    error = PermissionError("blocked")

    def fail_walk(root, topdown=True, onerror=None):
        assert root == tmp_path
        assert topdown is True
        assert onerror is not None
        onerror(error)
        yield from ()

    monkeypatch.setattr(os, "walk", fail_walk)

    with pytest.raises(PermissionError) as exc_info:
        list(_iter_source_files(tmp_path))

    assert exc_info.value is error


def test_no_raw_config_yaml_reads_outside_owner_modules():
    offenders: list[str] = []
    for rel, path in _iter_source_files():
        rel_str = str(rel).replace("\\", "/")
        if rel_str in ALLOWLIST:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        cfg_lines = [i for i, ln in enumerate(lines) if CONFIG_YAML_RE.search(ln)]
        if not cfg_lines:
            continue
        for i, ln in enumerate(lines):
            if not SAFE_LOAD_RE.search(ln):
                continue
            # Comment/docstring mentions don't count.
            stripped = ln.strip()
            if stripped.startswith("#"):
                continue
            if any(abs(i - j) <= PROXIMITY for j in cfg_lines):
                offenders.append(f"{rel_str}:{i + 1}: {stripped}")

    assert not offenders, (
        "Raw yaml.safe_load of config.yaml outside allowlisted owner modules.\n"
        "Behavioral reads must use hermes_cli.config.load_config()/"
        "load_config_readonly() (or gateway _load_gateway_config); write-back "
        "round-trips and raw-file diagnostics must use "
        "hermes_cli.config.read_user_config_raw().\nOffenders:\n  "
        + "\n  ".join(offenders)
    )


def test_read_user_config_raw_exists_and_documented():
    """The shared raw primitive must exist and carry its legality docstring."""
    from hermes_cli.config import read_user_config_raw

    doc = read_user_config_raw.__doc__ or ""
    assert "ONLY legal for write-back round-trips and raw-file diagnostics" in doc
    assert "load_config()" in doc
