"""
Nox sessions for the zitcompiler hatch AoT build backend integration tests.

@date: 10.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import shutil
from pathlib import Path

import nox

nox.options.default_venv_backend = "uv"

ZITCOMPILER_ROOT = Path(__file__).parent.parent.parent
PKG_DIR = Path(__file__).parent / "test_pkg"
DIST_DIR = Path(__file__).parent / "dist"
TESTS_FILE = Path(__file__).parent / "test_aot.py"


@nox.session
def test(session: nox.Session) -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir()

    # Install local zitcompiler as editable so the build hook and zetaclasses
    # can access .zig source files (core.zig etc.) from the source tree.
    session.install("hatchling", "-e", str(ZITCOMPILER_ROOT))

    # Build the test package. --no-build-isolation reuses the session's venv
    # (which already has zitcompiler) instead of creating an isolated build env,
    # so the hatch hook can be discovered and run.
    session.run(
        "uv",
        "build",
        "--directory",
        str(PKG_DIR),
        "--out-dir",
        str(DIST_DIR),
        "--no-build-isolation",
        external=True,
    )

    wheels = list(DIST_DIR.glob("*.whl"))
    assert len(wheels) == 1, f"Expected 1 wheel in {DIST_DIR}, found: {wheels}"
    wheel = wheels[0]

    session.install("pytest", str(wheel))
    session.run("pytest", str(TESTS_FILE), "-v")
