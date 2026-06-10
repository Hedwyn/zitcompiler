"""
Integration tests for the zitcompiler hatch AoT build backend.

Verifies that zit_compiled() artifacts are pre-compiled into the wheel
and that the installed package functions correctly.

@date: 10.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

from pathlib import Path


def test_aot_so_bundled() -> None:
    """The AoT-compiled .so for _native.zig must be present in the installed package."""
    import greetings  # noqa: PLC0415

    assert greetings.__file__ is not None
    pkg_dir = Path(greetings.__file__).parent
    so_files = list(pkg_dir.glob("_native___*.so"))
    assert so_files, (
        f"No AoT-compiled .so found in {pkg_dir}. "
        "Expected a file matching _native___<hash>.so bundled by the hatch hook."
    )


def test_hello_world() -> None:
    from greetings import hello_world

    hello_world()


def test_greeter() -> None:
    from greetings import Greeter

    g = Greeter(name="World")
    assert g.name == "World"


def test_point() -> None:
    from greetings import Point

    p = Point(x=3, y=4)
    assert p.x == 3
    assert p.y == 4


def test_color() -> None:
    from greetings import Color

    c = Color(r=255, g=0, b=128)
    assert c.r == 255
    assert c.g == 0
    assert c.b == 128
