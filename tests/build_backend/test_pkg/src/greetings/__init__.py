"""
Greetings package — test fixture for the zitcompiler hatch build backend.

@date: 10.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

from pathlib import Path

from zitcompiler import zitcompiled
from zitcompiler.zetaclasses import zetaclass

_HERE = Path(__file__).parent

hello_world = zitcompiled(_HERE / "_native.zig", "hello_world", "func")


@zetaclass
class Greeter:
    name: str


@zetaclass
class Point:
    x: int
    y: int


@zetaclass
class Color:
    r: int
    g: int
    b: int
