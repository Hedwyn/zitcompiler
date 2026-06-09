"""
Benchmarks for get/set logic.

@date: 08.06.2025
@author: Baptiste Pestourie
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchmarks.conftest import bench

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


class _Point:
    x: int
    y: int
    z: int


@bench(_Point)
def test_getattr(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    obj = cls(1, 2, 3)

    def getattr_loop() -> None:
        for _ in range(100):
            _ = obj.x
            _ = obj.y
            _ = obj.z

    benchmark(getattr_loop)


@bench(_Point)
def test_setattr(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    obj = cls(1, 2, 3)

    def setattr_loop() -> None:
        for i in range(100):
            obj.x = i
            obj.y = i + 1
            obj.z = i + 2

    benchmark(setattr_loop)
